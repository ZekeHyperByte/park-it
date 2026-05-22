# Preflight Validation

> 36 nodes · cohesion 0.07

## Key Concepts

- **check_deployment.py** (12 connections) — `scripts/check_deployment.py`
- **run_all_checks()** (11 connections) — `scripts/check_deployment.py`
- **test_check_deployment.py** (6 connections) — `scripts/tests/test_check_deployment.py`
- **check_ffmpeg()** (4 connections) — `scripts/check_deployment.py`
- **check_postgres()** (4 connections) — `scripts/check_deployment.py`
- **check_python_version()** (4 connections) — `scripts/check_deployment.py`
- **check_redis()** (4 connections) — `scripts/check_deployment.py`
- **check_user_groups()** (4 connections) — `scripts/check_deployment.py`
- **check_disk_space()** (3 connections) — `scripts/check_deployment.py`
- **check_memory()** (3 connections) — `scripts/check_deployment.py`
- **check_serial_ports()** (3 connections) — `scripts/check_deployment.py`
- **main()** (3 connections) — `scripts/check_deployment.py`
- **print_report()** (3 connections) — `scripts/check_deployment.py`
- **TestCheckDiskSpace** (3 connections) — `scripts/tests/test_check_deployment.py`
- **TestCheckFfmpeg** (2 connections) — `scripts/tests/test_check_deployment.py`
- **.test_ffmpeg_check()** (2 connections) — `scripts/tests/test_check_deployment.py`
- **TestCheckMemory** (2 connections) — `scripts/tests/test_check_deployment.py`
- **TestCheckPythonVersion** (2 connections) — `scripts/tests/test_check_deployment.py`
- **.test_returns_dict()** (2 connections) — `scripts/tests/test_check_deployment.py`
- **TestRunAllChecks** (2 connections) — `scripts/tests/test_check_deployment.py`
- **Deployment readiness checker.  Validates that the target system has all prerequi** (1 connections) — `scripts/check_deployment.py`
- **Check ffmpeg is installed.** (1 connections) — `scripts/check_deployment.py`
- **Check if current user is in dialout group.** (1 connections) — `scripts/check_deployment.py`
- **Run all deployment readiness checks.** (1 connections) — `scripts/check_deployment.py`
- **Print deployment readiness report. Return exit code.** (1 connections) — `scripts/check_deployment.py`
- *... and 11 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `scripts/check_deployment.py`
- `scripts/tests/test_check_deployment.py`

## Audit Trail

- EXTRACTED: 88 (93%)
- INFERRED: 7 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*