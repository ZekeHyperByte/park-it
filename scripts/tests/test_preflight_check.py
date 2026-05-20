"""Tests for preflight check script."""

from __future__ import annotations


from scripts.preflight_check import (
    PreflightCheck,
    PreflightRunner,
    check_disk_space,
    check_environment_variables,
    check_executables,
    check_memory,
    check_ports,
)


class TestPreflightCheck:
    def test_pass_status(self):
        check = PreflightCheck("test", "category")
        check.pass_("ok")
        assert check.status == "PASS"
        assert check.message == "ok"

    def test_warn_status(self):
        check = PreflightCheck("test", "category")
        check.warn("warning")
        assert check.status == "WARN"
        assert check.message == "warning"

    def test_fail_status(self):
        check = PreflightCheck("test", "category")
        check.fail("error")
        assert check.status == "FAIL"
        assert check.message == "error"

    def test_to_dict(self):
        check = PreflightCheck("test", "cat")
        check.pass_("ok")
        d = check.to_dict()
        assert d["name"] == "test"
        assert d["category"] == "cat"
        assert d["status"] == "PASS"


class TestPreflightRunner:
    def test_empty_summary(self):
        runner = PreflightRunner()
        summary = runner.summary()
        assert summary["total"] == 0
        assert summary["ready_for_deployment"] is True

    def test_all_pass(self):
        runner = PreflightRunner()
        c = PreflightCheck("x", "y")
        c.pass_()
        runner.add(c)
        assert runner.summary()["ready_for_deployment"] is True

    def test_one_fail(self):
        runner = PreflightRunner()
        c = PreflightCheck("x", "y")
        c.fail("bad")
        runner.add(c)
        assert runner.summary()["ready_for_deployment"] is False


class TestEnvironmentChecks:
    def test_checks_return_list(self):
        checks = check_environment_variables()
        assert isinstance(checks, list)
        assert len(checks) > 0


class SystemChecks:
    def test_disk_space_returns_list(self):
        checks = check_disk_space()
        assert isinstance(checks, list)
        assert len(checks) == 1
        assert checks[0].status in ("PASS", "WARN", "FAIL")

    def test_memory_returns_list(self):
        checks = check_memory()
        assert isinstance(checks, list)
        assert len(checks) == 1
        assert checks[0].status in ("PASS", "WARN", "FAIL")

    def test_ports_returns_list(self):
        checks = check_ports()
        assert isinstance(checks, list)
        assert len(checks) > 0

    def test_executables_returns_list(self):
        checks = check_executables()
        assert isinstance(checks, list)
        assert len(checks) > 0
