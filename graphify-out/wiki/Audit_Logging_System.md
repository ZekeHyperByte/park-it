# Audit Logging System

> 31 nodes · cohesion 0.10

## Key Concepts

- **AuditLog** (15 connections) — `api/app/models/audit_log.py`
- **test_audit_log.py** (13 connections) — `api/tests/test_audit_log.py`
- **log_action()** (11 connections) — `api/app/services/audit.py`
- **audit.py** (6 connections) — `api/app/services/audit.py`
- **log_payment()** (5 connections) — `api/app/services/audit.py`
- **log_user_management()** (5 connections) — `api/app/services/audit.py`
- **log_gate_operation()** (4 connections) — `api/app/services/audit.py`
- **log_setting_change()** (4 connections) — `api/app/services/audit.py`
- **audit_log.py** (2 connections) — `api/app/models/audit_log.py`
- **test_create_basic_log()** (2 connections) — `api/tests/test_audit_log.py`
- **test_create_minimal_log()** (2 connections) — `api/tests/test_audit_log.py`
- **test_log_cash_payment()** (2 connections) — `api/tests/test_audit_log.py`
- **test_log_manual_open()** (2 connections) — `api/tests/test_audit_log.py`
- **test_log_setting_update()** (2 connections) — `api/tests/test_audit_log.py`
- **test_log_user_create()** (2 connections) — `api/tests/test_audit_log.py`
- **test_none_details_becomes_empty_dict()** (2 connections) — `api/tests/test_audit_log.py`
- **TestLogAction** (2 connections) — `api/tests/test_audit_log.py`
- **TestLogGateOperation** (2 connections) — `api/tests/test_audit_log.py`
- **TestLogPayment** (2 connections) — `api/tests/test_audit_log.py`
- **TestLogSettingChange** (2 connections) — `api/tests/test_audit_log.py`
- **TestLogUserManagement** (2 connections) — `api/tests/test_audit_log.py`
- **.__repr__()** (1 connections) — `api/app/models/audit_log.py`
- **Audit log model for tracking sensitive operations.** (1 connections) — `api/app/models/audit_log.py`
- **Audit log entry for compliance and security monitoring.      Tracks all sensitiv** (1 connections) — `api/app/models/audit_log.py`
- **Audit logging service.  Provides helper functions for creating audit log entries** (1 connections) — `api/app/services/audit.py`
- *... and 6 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/app/models/audit_log.py`
- `api/app/services/audit.py`
- `api/tests/test_audit_log.py`

## Audit Trail

- EXTRACTED: 67 (68%)
- INFERRED: 32 (32%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*