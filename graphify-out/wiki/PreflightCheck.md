# PreflightCheck

> God node · 25 connections · `scripts/preflight_check.py`

## Connections by Relation

### calls
- [[check_environment_variables()]] `EXTRACTED`
- [[check_ports()]] `EXTRACTED`
- [[check_disk_space()]] `EXTRACTED`
- [[check_executables()]] `EXTRACTED`
- [[check_memory()]] `EXTRACTED`
- [[check_database()]] `EXTRACTED`
- [[check_redis()]] `EXTRACTED`
- [[check_directories()]] `EXTRACTED`
- [[.test_all_pass()]] `INFERRED`
- [[.test_one_fail()]] `INFERRED`
- [[.test_pass_status()]] `INFERRED`
- [[.test_warn_status()]] `INFERRED`
- [[.test_fail_status()]] `INFERRED`
- [[.test_to_dict()]] `INFERRED`

### contains
- [[preflight_check.py]] `EXTRACTED`

### method
- [[.pass_()]] `EXTRACTED`
- [[.fail()]] `EXTRACTED`
- [[.warn()]] `EXTRACTED`
- [[.to_dict()]] `EXTRACTED`
- [[.__init__()]] `EXTRACTED`

### rationale_for
- [[A single preflight check with status and message.]] `EXTRACTED`

### uses
- [[TestPreflightCheck]] `INFERRED`
- [[SystemChecks]] `INFERRED`
- [[TestPreflightRunner]] `INFERRED`
- [[TestEnvironmentChecks]] `INFERRED`

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*