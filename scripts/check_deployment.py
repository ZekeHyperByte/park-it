"""Deployment readiness checker.

Validates that the target system has all prerequisites for running
the parking system daemons and API.

Usage:
    python scripts/check_deployment.py
"""

import os
import platform
import shutil
import socket
import sys


def check_python_version() -> dict:
    """Check Python version is 3.12+."""
    version = sys.version_info
    ok = version.major == 3 and version.minor >= 12
    return {
        "name": "Python Version",
        "status": "ok" if ok else "fail",
        "message": f"{version.major}.{version.minor}.{version.micro}",
        "required": ">= 3.12",
    }


def check_redis(host: str = "localhost", port: int = 6379) -> dict:
    """Check Redis connectivity."""
    try:
        sock = socket.create_connection((host, port), timeout=2)
        sock.sendall(b"PING\r\n")
        response = sock.recv(1024)
        sock.close()
        ok = b"PONG" in response
        return {
            "name": "Redis",
            "status": "ok" if ok else "fail",
            "message": f"{host}:{port} -- {'PONG' if ok else 'Unexpected response'}",
        }
    except Exception as e:
        return {"name": "Redis", "status": "fail", "message": str(e)}


def check_postgres(host: str = "localhost", port: int = 5432) -> dict:
    """Check PostgreSQL connectivity."""
    try:
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        return {
            "name": "PostgreSQL",
            "status": "ok",
            "message": f"{host}:{port} -- TCP connect OK",
        }
    except Exception as e:
        return {"name": "PostgreSQL", "status": "fail", "message": str(e)}


def check_disk_space(min_gb: float = 10.0) -> dict:
    """Check available disk space."""
    stat = shutil.disk_usage("/")
    free_gb = stat.free / (1024 ** 3)
    ok = free_gb >= min_gb
    return {
        "name": "Disk Space",
        "status": "ok" if ok else "warn",
        "message": f"{free_gb:.1f} GB free (min: {min_gb} GB)",
    }


def check_memory(min_gb: float = 2.0) -> dict:
    """Check available memory."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024 ** 3)
        ok = available_gb >= min_gb
        return {
            "name": "Memory",
            "status": "ok" if ok else "warn",
            "message": f"{available_gb:.1f} GB available (min: {min_gb} GB)",
        }
    except ImportError:
        return {
            "name": "Memory",
            "status": "warn",
            "message": "psutil not installed -- cannot check memory",
        }


def check_serial_ports() -> dict:
    """List available serial ports."""
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        port_list = [p.device for p in ports]
        return {
            "name": "Serial Ports",
            "status": "ok" if port_list else "warn",
            "message": f"Found {len(port_list)} port(s): {', '.join(port_list) or 'None'}",
        }
    except ImportError:
        return {
            "name": "Serial Ports",
            "status": "warn",
            "message": "pyserial not installed -- cannot enumerate ports",
        }


def check_ffmpeg() -> dict:
    """Check ffmpeg is installed."""
    path = shutil.which("ffmpeg")
    return {
        "name": "ffmpeg",
        "status": "ok" if path else "warn",
        "message": path or "ffmpeg not found in PATH -- RTSP snapshots will fail",
    }


def check_user_groups() -> dict:
    """Check if current user is in dialout group."""
    try:
        import grp
        groups = [g.gr_name for g in grp.getgrall() if os.getlogin() in g.gr_mem or g.gr_gid == os.getgid()]
        in_dialout = "dialout" in groups
        return {
            "name": "User Groups",
            "status": "ok" if in_dialout else "warn",
            "message": f"dialout group: {'yes' if in_dialout else 'no -- serial access may fail'}",
        }
    except Exception as e:
        return {"name": "User Groups", "status": "warn", "message": str(e)}


def run_all_checks() -> list[dict]:
    """Run all deployment readiness checks."""
    checks = [
        check_python_version(),
        check_redis(),
        check_postgres(),
        check_disk_space(),
        check_memory(),
        check_serial_ports(),
        check_ffmpeg(),
        check_user_groups(),
    ]
    return checks


def print_report(checks: list[dict]) -> int:
    """Print deployment readiness report. Return exit code."""
    print(f"{'='*60}")
    print("Parking System -- Deployment Readiness Check")
    print(f"{'='*60}")

    fail_count = 0
    warn_count = 0

    for check in checks:
        status = check["status"]
        icon = "PASS" if status == "ok" else "WARN" if status == "warn" else "FAIL"
        if status == "fail":
            fail_count += 1
        elif status == "warn":
            warn_count += 1
        print(f"{icon} {check['name']:<20} {status.upper():<6} {check['message']}")

    print(f"{'='*60}")
    print(f"Result: {len(checks) - fail_count - warn_count}/{len(checks)} passed, {warn_count} warnings, {fail_count} failures")
    print(f"{'='*60}")

    return 1 if fail_count > 0 else 0


def main():
    checks = run_all_checks()
    sys.exit(print_report(checks))


if __name__ == "__main__":
    main()
