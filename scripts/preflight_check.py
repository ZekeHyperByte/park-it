#!/usr/bin/env python3
"""Pre-flight verification script for E-Parking v2 go-live.

Runs a comprehensive check of all system prerequisites before deployment.
Exits with code 0 if all checks pass, 1 if any critical check fails.

Usage:
    python scripts/preflight_check.py
    python scripts/preflight_check.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.config import get_settings
from shared.logging import configure_logging, get_logger
from shared.redis import redis_client

logger = get_logger("preflight")


class PreflightCheck:
    """A single preflight check with status and message."""

    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.status: str = "PENDING"
        self.message: str = ""
        self.duration_ms: float = 0.0

    def pass_(self, message: str = ""):
        self.status = "PASS"
        self.message = message or "OK"

    def warn(self, message: str):
        self.status = "WARN"
        self.message = message

    def fail(self, message: str):
        self.status = "FAIL"
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
        }


class PreflightRunner:
    """Runs all preflight checks and aggregates results."""

    def __init__(self):
        self.checks: list[PreflightCheck] = []
        self.start_time = time.time()

    def add(self, check: PreflightCheck) -> PreflightCheck:
        self.checks.append(check)
        return check

    def summary(self) -> dict[str, Any]:
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.status == "PASS")
        warnings = sum(1 for c in self.checks if c.status == "WARN")
        failed = sum(1 for c in self.checks if c.status == "FAIL")
        pending = sum(1 for c in self.checks if c.status == "PENDING")

        return {
            "total": total,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "pending": pending,
            "duration_seconds": round(time.time() - self.start_time, 2),
            "ready_for_deployment": failed == 0 and pending == 0,
        }

    def print_report(self, json_output: bool = False):
        if json_output:
            report = {
                "timestamp": datetime.now().isoformat(),
                "summary": self.summary(),
                "checks": [c.to_dict() for c in self.checks],
            }
            print(json.dumps(report, indent=2))
            return

        # Text report
        print("=" * 60)
        print("E-PARKING V2 — PREFLIGHT CHECK REPORT")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)

        current_category = ""
        for check in self.checks:
            if check.category != current_category:
                current_category = check.category
                print(f"\n[{current_category}]")

            icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "PENDING": "⏳"}.get(
                check.status, "?"
            )
            print(f"  {icon} {check.name}: {check.message}")

        summary = self.summary()
        print("\n" + "=" * 60)
        print(f"TOTAL: {summary['total']} | ✅ {summary['passed']} | ⚠️ {summary['warnings']} | ❌ {summary['failed']}")
        print(f"Duration: {summary['duration_seconds']}s")

        if summary["ready_for_deployment"]:
            print("\n🚀 SYSTEM READY FOR DEPLOYMENT")
        else:
            print("\n⛔ SYSTEM NOT READY — FIX FAILURES BEFORE DEPLOYING")
        print("=" * 60)


def check_environment_variables() -> list[PreflightCheck]:
    """Check required environment variables."""
    checks = []
    required_vars = [
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET",
        "APP_ENV",
    ]

    for var in required_vars:
        check = PreflightCheck(f"{var} set", "Environment")
        value = os.environ.get(var)
        if not value:
            check.fail("Not set")
        elif var == "JWT_SECRET" and len(value) < 32:
            check.warn(f"Set but only {len(value)} chars (recommend 64+)")
        else:
            check.pass_("Set")
        checks.append(check)

    # Check APP_ENV value
    check = PreflightCheck("APP_ENV is production", "Environment")
    app_env = os.environ.get("APP_ENV", "")
    if app_env == "production":
        check.pass_()
    elif app_env == "development":
        check.warn("development mode")
    else:
        check.fail(f"unexpected value: {app_env}")
    checks.append(check)

    return checks


def check_directories() -> list[PreflightCheck]:
    """Check required directories exist and are writable."""
    checks = []
    dirs = {
        "Settlement directory": os.environ.get("SETTLEMENT_DIR", "/var/lib/parking/settlements"),
        "Snapshot directory": os.environ.get("SNAPSHOT_DIR", "/var/lib/parking/snapshots"),
        "Log directory": "/var/log/parking",
    }

    for name, path_str in dirs.items():
        check = PreflightCheck(f"{name} ({path_str})", "Directories")
        path = Path(path_str)
        if not path.exists():
            check.fail("Does not exist")
        elif not os.access(path, os.W_OK):
            check.fail("Not writable")
        else:
            check.pass_()
        checks.append(check)

    return checks


def check_executables() -> list[PreflightCheck]:
    """Check required executables are available."""
    checks = []
    executables = {
        "ffmpeg": "Required for RTSP camera snapshots",
        "psql": "Required for database operations",
        "redis-cli": "Useful for Redis debugging",
    }

    for name, description in executables.items():
        check = PreflightCheck(f"{name}", "Executables")
        path = shutil.which(name)
        if path:
            check.pass_(path)
        else:
            check.warn(f"Not found — {description}")
        checks.append(check)

    return checks


def check_ports() -> list[PreflightCheck]:
    """Check required ports are available."""
    checks = []
    ports = {
        "API port (8000)": 8000,
        "PostgreSQL (5432)": 5432,
        "Redis (6379)": 6379,
    }

    for name, port in ports.items():
        check = PreflightCheck(name, "Ports")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                # Check if something is already listening
                result = s.connect_ex(("127.0.0.1", port))
                if result == 0:
                    check.pass_("Port in use (expected for existing services)")
                else:
                    check.pass_("Port available")
        except Exception as e:
            check.fail(str(e))
        checks.append(check)

    return checks


def check_disk_space() -> list[PreflightCheck]:
    """Check available disk space."""
    checks = []
    check = PreflightCheck("Disk space", "System")
    try:
        stat = shutil.disk_usage("/")
        free_gb = stat.free / (1024**3)
        total_gb = stat.total / (1024**3)
        if free_gb < 5:
            check.fail(f"Only {free_gb:.1f} GB free")
        elif free_gb < 10:
            check.warn(f"{free_gb:.1f} GB free (recommend 10+ GB)")
        else:
            check.pass_(f"{free_gb:.1f} GB free of {total_gb:.1f} GB")
    except Exception as e:
        check.fail(str(e))
    checks.append(check)
    return checks


def check_memory() -> list[PreflightCheck]:
    """Check available memory."""
    checks = []
    check = PreflightCheck("Memory", "System")
    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        for line in meminfo.split("\n"):
            if line.startswith("MemAvailable:"):
                available_kb = int(line.split()[1])
                available_gb = available_kb / (1024**2)
                if available_gb < 1:
                    check.fail(f"Only {available_gb:.1f} GB available")
                elif available_gb < 2:
                    check.warn(f"{available_gb:.1f} GB available (recommend 2+ GB)")
                else:
                    check.pass_(f"{available_gb:.1f} GB available")
                break
        else:
            check.warn("Could not parse /proc/meminfo")
    except Exception as e:
        check.warn(f"Could not check memory: {e}")
    checks.append(check)
    return checks


async def check_database() -> list[PreflightCheck]:
    """Check database connectivity."""
    checks = []
    check = PreflightCheck("PostgreSQL connectivity", "Database")
    try:
        settings = get_settings()
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            await result.scalar()
        await engine.dispose()
        check.pass_()
    except Exception as e:
        check.fail(str(e))
    checks.append(check)
    return checks


async def check_redis() -> list[PreflightCheck]:
    """Check Redis connectivity."""
    checks = []
    check = PreflightCheck("Redis connectivity", "Cache")
    try:
        await redis_client.connect()
        redis = redis_client.client
        await redis.ping()
        check.pass_()
    except Exception as e:
        check.fail(str(e))
    checks.append(check)
    return checks


async def run_all_checks() -> PreflightRunner:
    """Run all preflight checks."""
    runner = PreflightRunner()

    # Environment
    for check in check_environment_variables():
        runner.add(check)

    # Directories
    for check in check_directories():
        runner.add(check)

    # Executables
    for check in check_executables():
        runner.add(check)

    # Ports
    for check in check_ports():
        runner.add(check)

    # System
    for check in check_disk_space():
        runner.add(check)
    for check in check_memory():
        runner.add(check)

    # Database (async)
    for check in await check_database():
        runner.add(check)

    # Redis (async)
    for check in await check_redis():
        runner.add(check)

    return runner


def main():
    parser = argparse.ArgumentParser(description="E-Parking v2 Pre-flight Check")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    configure_logging()

    try:
        runner = asyncio.run(run_all_checks())
    except Exception as e:
        logger.error("preflight_failed", error=str(e))
        sys.exit(1)

    runner.print_report(json_output=args.json)

    summary = runner.summary()
    sys.exit(0 if summary["ready_for_deployment"] else 1)


if __name__ == "__main__":
    main()
