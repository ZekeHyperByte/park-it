"""Tests for deployment readiness checker."""


from scripts.check_deployment import (
    check_python_version,
    check_disk_space,
    check_memory,
    check_ffmpeg,
    run_all_checks,
)


class TestCheckPythonVersion:
    def test_returns_dict(self):
        result = check_python_version()
        assert isinstance(result, dict)
        assert "name" in result
        assert "status" in result
        assert "message" in result


class TestCheckDiskSpace:
    def test_disk_space_ok(self):
        result = check_disk_space(min_gb=0.001)
        assert result["status"] == "ok"
        assert "GB free" in result["message"]

    def test_disk_space_warn(self):
        result = check_disk_space(min_gb=999999)
        assert result["status"] == "warn"


class TestCheckMemory:
    def test_memory_returns_dict(self):
        result = check_memory()
        assert isinstance(result, dict)
        assert result["name"] == "Memory"
        assert result["status"] in ("ok", "warn")


class TestCheckFfmpeg:
    def test_ffmpeg_check(self):
        result = check_ffmpeg()
        assert isinstance(result, dict)
        assert result["name"] == "ffmpeg"
        # May be ok or warn depending on system
        assert result["status"] in ("ok", "warn")


class TestRunAllChecks:
    def test_returns_list(self):
        checks = run_all_checks()
        assert isinstance(checks, list)
        assert len(checks) == 8
        for check in checks:
            assert "name" in check
            assert "status" in check
            assert "message" in check
