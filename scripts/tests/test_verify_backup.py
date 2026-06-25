"""Tests for backup verification script."""

from __future__ import annotations

import gzip
import tempfile
from pathlib import Path

from scripts.verify_backup import (
    check_backup_contents,
    check_backup_exists,
    check_backup_integrity,
    find_latest_backup,
    verify_backup,
)


class TestFindLatestBackup:
    def test_no_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = find_latest_backup(tmp)
            assert result is None

    def test_finds_latest(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "parking_20260101_000000.sql.gz"
            new = Path(tmp) / "parking_20261231_000000.sql.gz"
            old.write_bytes(gzip.compress(b"old"))
            new.write_bytes(gzip.compress(b"new"))
            result = find_latest_backup(tmp)
            assert result == new


class TestCheckBackupExists:
    def test_missing_file(self):
        passed, msg = check_backup_exists(Path("/nonexistent"))
        assert passed is False
        assert "not found" in msg.lower()

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as f:
            f.write(b"")
            path = Path(f.name)
        passed, msg = check_backup_exists(path)
        path.unlink()
        assert passed is False
        assert "empty" in msg.lower()

    def test_valid_file(self):
        with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as f:
            f.write(gzip.compress(b"content"))
            path = Path(f.name)
        passed, msg = check_backup_exists(path)
        path.unlink()
        assert passed is True
        assert "MB" in msg


class TestCheckBackupIntegrity:
    def test_valid_gzip(self):
        with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as f:
            f.write(gzip.compress(b"CREATE TABLE test;"))
            path = Path(f.name)
        passed, msg = check_backup_integrity(path)
        path.unlink()
        assert passed is True
        assert "integrity verified" in msg.lower()

    def test_invalid_gzip(self):
        with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as f:
            f.write(b"not gzip data")
            path = Path(f.name)
        passed, msg = check_backup_integrity(path)
        path.unlink()
        assert passed is False


class TestCheckBackupContents:
    def test_postgresql_content(self):
        with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as f:
            f.write(gzip.compress(b"-- PostgreSQL database dump\nCREATE TABLE users;"))
            path = Path(f.name)
        passed, msg = check_backup_contents(path)
        path.unlink()
        assert passed is True
        assert "postgresql" in msg.lower()

    def test_non_postgresql_content(self):
        with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as f:
            f.write(gzip.compress(b"hello world"))
            path = Path(f.name)
        passed, msg = check_backup_contents(path)
        path.unlink()
        assert passed is False


class TestVerifyBackup:
    def test_full_verification_pass(self):
        with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as f:
            f.write(gzip.compress(b"-- PostgreSQL database dump\nCREATE TABLE test;"))
            path = Path(f.name)
        result = verify_backup(path, max_age_hours=9999)
        path.unlink()
        assert result["overall"] == "PASS"
        assert "exists" in result["checks"]
        assert "age" in result["checks"]
        assert "integrity" in result["checks"]
        assert "contents" in result["checks"]

    def test_full_verification_fail_missing(self):
        result = verify_backup(Path("/nonexistent"))
        assert result["overall"] == "FAIL"
