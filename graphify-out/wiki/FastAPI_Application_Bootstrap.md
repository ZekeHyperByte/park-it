# FastAPI Application Bootstrap

> 74 nodes · cohesion 0.05

## Key Concepts

- **PreflightCheck** (25 connections) — `scripts/preflight_check.py`
- **PreflightRunner** (14 connections) — `scripts/preflight_check.py`
- **run_all_checks()** (13 connections) — `scripts/preflight_check.py`
- **preflight_check.py** (12 connections) — `scripts/preflight_check.py`
- **.pass_()** (9 connections) — `scripts/preflight_check.py`
- **check_disk_space()** (8 connections) — `scripts/preflight_check.py`
- **check_environment_variables()** (8 connections) — `scripts/preflight_check.py`
- **check_ports()** (8 connections) — `scripts/preflight_check.py`
- **.fail()** (8 connections) — `scripts/preflight_check.py`
- **check_database()** (7 connections) — `scripts/preflight_check.py`
- **check_executables()** (7 connections) — `scripts/preflight_check.py`
- **check_memory()** (7 connections) — `scripts/preflight_check.py`
- **check_redis()** (7 connections) — `scripts/preflight_check.py`
- **configure_logging()** (7 connections) — `shared/logging.py`
- **SystemChecks** (7 connections) — `scripts/tests/test_preflight_check.py`
- **TestPreflightCheck** (7 connections) — `scripts/tests/test_preflight_check.py`
- **check_directories()** (6 connections) — `scripts/preflight_check.py`
- **main()** (6 connections) — `scripts/preflight_check.py`
- **TestPreflightRunner** (6 connections) — `scripts/tests/test_preflight_check.py`
- **_run_daemon()** (5 connections) — `daemons/cli.py`
- **.warn()** (5 connections) — `scripts/preflight_check.py`
- **test_preflight_check.py** (5 connections) — `scripts/tests/test_preflight_check.py`
- **logging.py** (5 connections) — `shared/logging.py`
- **cli.py** (4 connections) — `daemons/cli.py`
- **.print_report()** (4 connections) — `scripts/preflight_check.py`
- *... and 49 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/app/main.py`
- `daemons/cli.py`
- `scripts/preflight_check.py`
- `scripts/tests/test_preflight_check.py`
- `shared/logging.py`

## Audit Trail

- EXTRACTED: 226 (80%)
- INFERRED: 56 (20%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*