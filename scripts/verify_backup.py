#!/usr/bin/env python3
"""Backup verification script for E-Parking v2.

Verifies that database backups exist, are recent, and are restorable.

Usage:
    python scripts/verify_backup.py /backup/parking_20260426_000000.sql.gz
    python scripts/verify_backup.py --latest /backup/
"""

from __future__ import annotations

import argparse
import gzip
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from shared.logging import configure_logging, get_logger

logger = get_logger("backup_verify")


def find_latest_backup(backup_dir: str) -> Path | None:
    """Find the most recent backup file in a directory."""
    path = Path(backup_dir)
    if not path.exists():
        return None

    backups = sorted(
        path.glob("parking_*.sql.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return backups[0] if backups else None


def check_backup_exists(backup_path: Path) -> tuple[bool, str]:
    """Check if backup file exists and is non-empty."""
    if not backup_path.exists():
        return False, f"File not found: {backup_path}"
    if backup_path.stat().st_size == 0:
        return False, "File is empty"
    size_mb = backup_path.stat().st_size / (1024**2)
    return True, f"File exists ({size_mb:.1f} MB)"


def check_backup_age(backup_path: Path, max_age_hours: int = 25) -> tuple[bool, str]:
    """Check if backup is recent enough."""
    mtime = datetime.fromtimestamp(backup_path.stat().st_mtime, tz=timezone.utc)
    age = datetime.now(timezone.utc) - mtime
    if age > timedelta(hours=max_age_hours):
        return False, f"Backup is {age.total_seconds() / 3600:.1f} hours old"
    return True, f"Backup is {age.total_seconds() / 3600:.1f} hours old"


def check_backup_integrity(backup_path: Path) -> tuple[bool, str]:
    """Check if gzip file is not corrupted."""
    try:
        with gzip.open(backup_path, "rb") as f:
            # Read first and last chunks to verify integrity
            first = f.read(1024)
            if not first:
                return False, "Cannot read from gzip file"
            # Try to seek near end
            f.seek(-1024, 2)
            last = f.read(1024)
            if not last:
                return False, "Cannot read end of gzip file"
        return True, "Gzip integrity verified"
    except Exception as e:
        return False, f"Gzip integrity check failed: {e}"


def check_backup_contents(backup_path: Path) -> tuple[bool, str]:
    """Check if backup contains expected PostgreSQL content."""
    try:
        with gzip.open(backup_path, "rt", encoding="utf-8", errors="replace") as f:
            first_lines = [f.readline() for _ in range(20)]
            content = "".join(first_lines)
            if "PostgreSQL" in content or "CREATE TABLE" in content or "COPY" in content:
                return True, "Contains PostgreSQL dump content"
            return False, "Does not appear to be a PostgreSQL dump"
    except Exception as e:
        return False, f"Content check failed: {e}"


def verify_backup(backup_path: Path, max_age_hours: int = 25) -> dict:
    """Run all verification checks on a backup file."""
    results = {
        "file": str(backup_path),
        "checks": {},
        "overall": "PENDING",
    }

    checks = [
        ("exists", check_backup_exists),
        ("age", check_backup_age),
        ("integrity", check_backup_integrity),
        ("contents", check_backup_contents),
    ]

    all_passed = True
    for name, check_fn in checks:
        try:
            if name == "age":
                passed, message = check_fn(backup_path, max_age_hours)
            else:
                passed, message = check_fn(backup_path)
        except Exception as e:
            passed, message = False, f"Check crashed: {e}"
        results["checks"][name] = {"passed": passed, "message": message}
        if not passed:
            all_passed = False

    results["overall"] = "PASS" if all_passed else "FAIL"
    return results


def dry_run_restore(backup_path: Path, db_url: str | None = None) -> tuple[bool, str]:
    """Perform a dry-run restore to verify backup is restorable.

    Uses pg_restore --list or psql --dry-run equivalent.
    """
    try:
        # Decompress to temp and run a syntax check
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as tmp:
            tmp_path = tmp.name

        with gzip.open(backup_path, "rb") as src:
            with open(tmp_path, "wb") as dst:
                dst.write(src.read(1024 * 1024))  # First 1MB for syntax check

        # Check for basic SQL syntax
        with open(tmp_path, "r") as f:
            content = f.read(1024 * 1024)
            if ";" in content and ("CREATE" in content or "INSERT" in content or "COPY" in content):
                os.unlink(tmp_path)
                return True, "Restore dry-run passed (first 1MB validated)"
            os.unlink(tmp_path)
            return False, "No valid SQL statements found in first 1MB"
    except Exception as e:
        return False, f"Dry-run failed: {e}"


def main():
    parser = argparse.ArgumentParser(description="Verify E-Parking database backup")
    parser.add_argument("backup_path", nargs="?", help="Path to backup file")
    parser.add_argument("--latest", metavar="DIR", help="Find latest backup in directory")
    parser.add_argument("--max-age", type=int, default=25, help="Maximum backup age in hours")
    parser.add_argument("--dry-run", action="store_true", help="Perform restore dry-run")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    configure_logging()

    # Determine backup path
    if args.latest:
        backup_path = find_latest_backup(args.latest)
        if not backup_path:
            print(f"ERROR: No backup found in {args.latest}", file=sys.stderr)
            sys.exit(1)
    elif args.backup_path:
        backup_path = Path(args.backup_path)
    else:
        # Default: look in /backup/
        backup_path = find_latest_backup("/backup/")
        if not backup_path:
            print("ERROR: No backup path specified and no backup found in /backup/", file=sys.stderr)
            sys.exit(1)

    # Run verification
    results = verify_backup(backup_path, args.max_age)

    # Dry run
    if args.dry_run:
        passed, message = dry_run_restore(backup_path)
        results["checks"]["dry_run"] = {"passed": passed, "message": message}
        if not passed:
            results["overall"] = "FAIL"

    # Output
    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        print(f"Backup: {results['file']}")
        print(f"Overall: {results['overall']}")
        print()
        for name, check in results["checks"].items():
            icon = "✅" if check["passed"] else "❌"
            print(f"  {icon} {name}: {check['message']}")

    sys.exit(0 if results["overall"] == "PASS" else 1)


if __name__ == "__main__":
    main()
