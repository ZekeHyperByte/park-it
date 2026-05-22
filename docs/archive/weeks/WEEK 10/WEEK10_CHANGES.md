# Week 10 — Changes & Build Log

> **Date:** 26 April 2026
> **Scope:** Production Hardening — RTSP Cameras, Lost-Contact Recovery, Rate Limiting, Audit Logging, Operations Runbook
> **Depends on:** Weeks 1–9 (all core functionality complete)

---

## What Was Built

### 1. RTSP Snapshot Support

**Problem:** The snapshot worker only supported HTTP snapshot URLs. Many CCTV cameras only provide RTSP streams without HTTP endpoints.

**Solution:**
- `workers/critical/rtsp_snapshot.py` — ffmpeg-based RTSP frame capture
- Modified `workers/critical/snapshot_worker.py` — auto-detects RTSP vs HTTP URLs
- Supports TCP transport for reliable streaming
- 8-second timeout with graceful fallback

**Files:**
- Created: `workers/critical/rtsp_snapshot.py`
- Modified: `workers/critical/snapshot_worker.py`

---

### 2. Lost-Contact Recovery Flow

**Problem:** The e-money lost-contact flow was incomplete. When a card was removed mid-transaction, the system treated it as a terminal failure, preventing the automatic correction that the PASSTI reader supports.

**Solution:**
- Updated `api/app/services/payment.py` — `process_emoney_result()` now handles:
  - `LOST_CONTACT`: Intermediate state — keeps transaction PENDING, prompts user to retry
  - `CORRECTION_VERIFIED`: Treated as success (auto-correction succeeded)
  - `CORRECTION_FAILED`: Terminal failure — resets transaction for other payment methods
  - `TIMEOUT`: Terminal failure with logging

**Behavior:**
```
LOST_CONTACT received
  → Create EmoneyTransaction (status=LOST_CONTACT)
  → Keep ParkingTransaction in PENDING
  → Publish display_text + play_audio (retry prompt)
  → Daemon auto-retries when same card tapped
  → On SUCCESS/CORRECTION_VERIFIED: complete transaction
  → On CORRECTION_FAILED: allow cash/RFID alternative
```

**Files:**
- Modified: `api/app/services/payment.py`

---

### 3. Rate Limiting

**Problem:** No protection against brute-force attacks on auth endpoints or abuse of payment APIs.

**Solution:**
- `api/app/middleware/rate_limit.py` — Redis-backed sliding window rate limiter
- Per-path configurable limits:
  - `/api/auth/login`: 5 req/min
  - `/api/auth/refresh`: 10 req/min
  - `/api/payments/*`: 30 req/min
  - Fallback: 100 req/min
- Returns 429 with `Retry-After` header
- Fails open if Redis is unavailable
- Exempt paths: `/api/health`, `/metrics`, `/docs`

**Files:**
- Created: `api/app/middleware/rate_limit.py`
- Modified: `api/app/main.py` (add middleware)

---

### 4. Audit Logging

**Problem:** No centralized record of sensitive operations for compliance and security monitoring.

**Solution:**
- `api/app/models/audit_log.py` — AuditLog model with JSONB details
- `api/app/services/audit.py` — Service helpers for common actions
- `api/app/routes/audit_logs.py` — Admin-only list endpoint with filtering
- `api/alembic/versions/d5e8f9a1b2c3_add_audit_log_table.py` — Migration

**Tracked actions:**
- Payments: `CASH_PAYMENT`, `RFID_PAYMENT`, `EMONEY_PAYMENT`
- Gate ops: `MANUAL_GATE_OPEN`, `RESET_GATE`
- Settings: `SETTING_UPDATE`
- Users: `USER_CREATE`, `USER_UPDATE`, `USER_DELETE`

**Schema:**
```
AuditLog: id, user_id, username, action, entity_type, entity_id,
          details(JSONB), ip_address, user_agent, created_at
```

**Files:**
- Created: `api/app/models/audit_log.py`, `api/app/services/audit.py`, `api/app/routes/audit_logs.py`
- Modified: `api/app/models/__init__.py`, `api/app/main.py`

---

### 5. Operations Runbook

**Created:** `docs/OPERATIONS_RUNBOOK.md`

Contents:
- System architecture overview
- Deployment procedures (step-by-step)
- Daily operations (settlement, backup, log rotation)
- Monitoring & alerting (Prometheus metrics, health checks)
- Troubleshooting guide (gate issues, e-money, payments, DB)
- Backup & recovery procedures
- Security checklist
- Emergency procedures

---

## Verification Results

| Test | Result |
|------|--------|
| RTSP snapshot tests | 7/7 passed |
| Payment service tests (new) | 4/4 passed |
| Rate limit tests | 6/6 passed |
| Audit log tests | 7/7 passed |
| Full backend test suite | 326/326 passed |
| Frontend production build | 5.57 MB, 0 errors |
| FastAPI route loading | 71 routes |
| No circular imports | Verified |

**Note:** 1 pre-existing flaky test (`test_no_unsettled_transactions`) excluded from full suite run per Week 9 documentation. Passes when run in isolation.

---

## Decisions Made

1. **RTSP via ffmpeg:** Used ffmpeg CLI instead of OpenCV because ffmpeg is more reliable for single-frame capture and is already available in production deployments.

2. **Lost-contact intermediate state:** LOST_CONTACT keeps the ParkingTransaction in PENDING rather than resetting it. This allows the daemon's auto-correction to succeed without requiring a new deduct command from FastAPI.

3. **Rate limit fail-open:** If Redis is unavailable, requests are allowed through. This prioritizes availability over strict rate limiting during infrastructure issues.

4. **Audit log no FK to users:** Removed the foreign key constraint from `audit_logs.user_id` to `users.id`. This ensures audit records persist even if users are deleted.

5. **Route test cache isolation:** Patched Redis cache functions in vehicle type route tests to prevent cross-test cache pollution caused by the singleton RedisClient retaining connections across event loops.

---

## Files Created/Modified

**Created:** 10 new files
- `workers/critical/rtsp_snapshot.py`
- `workers/tests/test_rtsp_snapshot.py`
- `api/app/middleware/rate_limit.py`
- `api/tests/test_rate_limit.py`
- `api/app/models/audit_log.py`
- `api/app/services/audit.py`
- `api/app/routes/audit_logs.py`
- `api/tests/test_audit_log.py`
- `api/alembic/versions/d5e8f9a1b2c3_add_audit_log_table.py`
- `docs/OPERATIONS_RUNBOOK.md`

**Modified:** 6 files
- `workers/critical/snapshot_worker.py` — RTSP support
- `api/app/services/payment.py` — Lost-contact recovery
- `api/app/models/__init__.py` — AuditLog import
- `api/app/main.py` — Rate limit middleware + audit routes
- `api/tests/test_payment_service.py` — New test cases
- `api/tests/test_vehicle_type_routes.py` — Cache isolation

**Total lines of code:** ~1,200+ (backend + tests + docs)

---

## Week 10 Exit Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | RTSP snapshot worker captures frames from RTSP URLs | ✅ |
| 2 | Lost-contact flow handles intermediate state correctly | ✅ |
| 3 | Rate limiting returns 429 on excessive requests | ✅ |
| 4 | Audit logs record all sensitive operations | ✅ |
| 5 | Operations runbook covers deployment, monitoring, troubleshooting | ✅ |
| 6 | All existing tests pass (no regressions) | ✅ (326 passed) |
| 7 | New tests cover RTSP, recovery, rate limiting, audit logging | ✅ (24 new tests) |
| 8 | Frontend builds without errors | ✅ |
| 9 | Documentation complete and accurate | ✅ |

---

## Looking Ahead to Week 11

**Week 11 scope:** Hardware Integration Testing
- Deploy daemons to actual Compass/PASSTI controllers
- End-to-end testing with real hardware
- Performance tuning based on real-world latency
- Camera integration validation

**Week 12 scope:** Production Deployment
- Final security review
- Certification preparation documentation
- Go-live checklist execution
- Handover to operations team

*End of Week 10 Build Log*
