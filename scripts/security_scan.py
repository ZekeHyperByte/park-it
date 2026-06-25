#!/usr/bin/env python3
"""Dependency security scanner for E-Parking v2.

Scans Python and Node.js dependencies for known security vulnerabilities.

Usage:
    python scripts/security_scan.py
    python scripts/security_scan.py --json
    python scripts/security_scan.py --fail-on warn
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from typing import Any

from shared.logging import configure_logging, get_logger

logger = get_logger("security_scan")


class SecurityScanner:
    """Runs security scans and aggregates results."""

    def __init__(self):
        self.results: list[dict[str, Any]] = []

    def run_command(self, cmd: list[str], description: str) -> dict[str, Any]:
        """Run a command and capture output."""
        result = {
            "tool": description,
            "command": " ".join(cmd),
            "status": "PENDING",
            "output": "",
            "findings": [],
        }
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            result["output"] = proc.stdout + proc.stderr
            result["returncode"] = proc.returncode

            if proc.returncode == 0:
                result["status"] = "PASS"
            elif proc.returncode == 1:
                # Some tools return 1 for findings
                result["status"] = "WARN"
            else:
                result["status"] = "ERROR"
        except FileNotFoundError:
            result["status"] = "NOT_INSTALLED"
            result["output"] = f"{cmd[0]} not found. Install with: pip install {cmd[0]}"
        except subprocess.TimeoutExpired:
            result["status"] = "TIMEOUT"
            result["output"] = "Command timed out after 120 seconds"
        except Exception as e:
            result["status"] = "ERROR"
            result["output"] = str(e)

        return result

    def scan_pip_audit(self) -> dict[str, Any]:
        """Scan Python packages with pip-audit."""
        result = self.run_command(
            ["pip-audit", "--format=json", "--desc"],
            "pip-audit (Python CVE scan)",
        )
        if result["status"] == "NOT_INSTALLED":
            return result

        try:
            data = json.loads(result["output"])
            vulnerabilities = data.get("vulnerabilities", [])
            result["findings"] = [
                {
                    "package": v.get("name"),
                    "version": v.get("version"),
                    "vulnerability_id": vuln.get("id"),
                    "description": vuln.get("description", "")[:200],
                    "fix_versions": vuln.get("fix_versions", []),
                }
                for v in vulnerabilities
                for vuln in v.get("vulns", [])
            ]
            if result["findings"]:
                result["status"] = "FAIL" if any(
                    f["vulnerability_id"] for f in result["findings"]
                ) else "WARN"
        except json.JSONDecodeError:
            # pip-audit might not output JSON on error
            if "No known vulnerabilities found" in result["output"]:
                result["status"] = "PASS"
                result["findings"] = []

        return result

    def scan_safety(self) -> dict[str, Any]:
        """Scan Python packages with safety."""
        result = self.run_command(
            ["safety", "check", "--json"],
            "safety (Python CVE scan)",
        )
        if result["status"] == "NOT_INSTALLED":
            return result

        try:
            data = json.loads(result["output"])
            result["findings"] = data if isinstance(data, list) else []
            if result["findings"]:
                result["status"] = "FAIL"
            else:
                result["status"] = "PASS"
        except json.JSONDecodeError:
            if "No known security vulnerabilities" in result["output"]:
                result["status"] = "PASS"
                result["findings"] = []

        return result

    def scan_npm_audit(self) -> dict[str, Any]:
        """Scan Node.js packages with npm audit."""
        result = self.run_command(
            ["npm", "audit", "--json"],
            "npm audit (Node.js CVE scan)",
        )
        if result["status"] == "NOT_INSTALLED":
            return result

        try:
            data = json.loads(result["output"])
            vulnerabilities = data.get("vulnerabilities", {})
            advisories = data.get("advisories", {})

            # npm audit --json format varies by version
            if vulnerabilities:
                result["findings"] = [
                    {"package": k, **v}
                    for k, v in vulnerabilities.items()
                ]
            elif advisories:
                result["findings"] = [
                    {"package": k, **v}
                    for k, v in advisories.items()
                ]
            else:
                result["findings"] = []

            # npm audit returns 0 when no vulnerabilities
            if result["returncode"] == 0 or not result["findings"]:
                result["status"] = "PASS"
            else:
                result["status"] = "FAIL"
        except json.JSONDecodeError:
            if "found 0 vulnerabilities" in result["output"]:
                result["status"] = "PASS"
                result["findings"] = []

        return result

    def run_all(self) -> dict[str, Any]:
        """Run all available scanners."""
        self.results = []

        scanners = [
            self.scan_pip_audit,
            self.scan_safety,
            self.scan_npm_audit,
        ]

        for scanner in scanners:
            result = scanner()
            self.results.append(result)

        # Determine overall status
        statuses = [r["status"] for r in self.results]
        if "FAIL" in statuses:
            overall = "FAIL"
        elif "WARN" in statuses or "ERROR" in statuses or "NOT_INSTALLED" in statuses:
            overall = "WARN"
        else:
            overall = "PASS"

        return {
            "timestamp": datetime.now().isoformat(),
            "overall": overall,
            "results": self.results,
        }


def main():
    parser = argparse.ArgumentParser(description="E-Parking v2 Security Scan")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument(
        "--fail-on",
        choices=["fail", "warn"],
        default="fail",
        help="Exit with error on FAIL or WARN",
    )
    args = parser.parse_args()

    configure_logging()
    scanner = SecurityScanner()
    report = scanner.run_all()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 60)
        print("E-PARKING V2 — SECURITY SCAN REPORT")
        print(f"Timestamp: {report['timestamp']}")
        print("=" * 60)

        for result in report["results"]:
            status_icon = {
                "PASS": "✅",
                "WARN": "⚠️",
                "FAIL": "❌",
                "ERROR": "❌",
                "NOT_INSTALLED": "⏳",
            }.get(result["status"], "?")
            print(f"\n{status_icon} {result['tool']}: {result['status']}")
            if result["findings"]:
                print(f"   Findings: {len(result['findings'])}")
                for finding in result["findings"][:5]:
                    pkg = finding.get("package", "unknown")
                    print(f"   - {pkg}")
            if result["status"] == "NOT_INSTALLED":
                print(f"   {result['output']}")

        print("\n" + "=" * 60)
        overall_icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(
            report["overall"], "?"
        )
        print(f"OVERALL: {overall_icon} {report['overall']}")
        print("=" * 60)

    # Exit code
    if report["overall"] == "FAIL":
        sys.exit(1)
    if args.fail_on == "warn" and report["overall"] == "WARN":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
