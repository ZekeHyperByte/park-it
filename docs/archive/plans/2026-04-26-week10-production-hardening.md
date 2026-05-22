# Week 10 — Production Hardening & Final Integration Plan

> **Date:** 26 April 2026
> **Scope:** RTSP Camera Support, Lost-Contact Recovery, Rate Limiting, Audit Logging, Operations Runbook
> **Depends on:** Weeks 1–9 (all core functionality complete)

---

## Task 1: RTSP Snapshot Support

**Goal:** Enable the snapshot worker to capture frames from RTSP cameras, not just HTTP snapshot URLs.

**Files:**
- Create: `workers/critical/rtsp_snapshot.py`
- Modify: `workers/critical/snapshot_worker.py`
- Test: `workers/tests/test_rtsp_snapshot.py`

**Implementation:**
- Use `ffmpeg` CLI (subprocess) to extract a single frame from RTSP stream
- Fallback to `opencv-python` if ffmpeg is not available
- Timeout: 5 seconds max per snapshot
- Save as JPEG with same naming convention as HTTP snapshots

**Test approach:**
- Mock subprocess to test ffmpeg invocation
- Test fallback behavior when ffmpeg unavailable
- Test timeout handling

---

## Task 2: Lost-Contact Recovery Flow

**Goal:** Complete the e-money lost-contact recovery flow per the PASSTI spec and development plan.

**Current state:**
- Daemon publishes `LOST_CONTACT` status when card removed mid-transaction
- Payment service treats it as a failure and resets transaction
- **Missing:** Intermediate state handling, auto-correction retry, GetLastTransaction verification on timeout

**Files:**
- Modify: `api/app/services/payment.py` — `process_emoney_result()` to handle LOST_CONTACT as intermediate
- Modify: `api/app/models/emoney_transaction.py` — Add `correction_attempts` field, `LOST_CONTACT` status
- Create: `api/app/services/emoney_recovery.py` — Recovery orchestrator
- Test: `api/tests/test_emoney_recovery.py`

**Flow:**
```
LOST_CONTACT received
  → Create EmoneyTransaction with status=LOST_CONTACT
  → Publish "display_text" + "play_audio" (track 7: retry same card)
  → Do NOT reset transaction (keep PENDING)
  → Daemon will auto-retry when same card tapped
  → On SUCCESS (auto-correction): update EmoneyTransaction to SUCCESS, complete transaction
  → On CORRECTION_FAILED: update to CORRECTION_FAILED, reset transaction for other payment methods
```

**TIMEOUT verification (daemon side):**
- When deduct times out, daemon runs `GetLastTransaction`
- Verifies `card_number + deduct_amount + transaction_counter` all match
- Only if all three match → treat as SUCCESS
- Any mismatch → FAILED

---

## Task 3: Rate Limiting

**Goal:** Prevent brute-force attacks on auth and abuse of payment endpoints.

**Files:**
- Create: `api/app/middleware/rate_limit.py`
- Modify: `api/app/main.py` — Add rate limit middleware
- Modify: `api/app/routes/auth.py` — Apply rate limits
- Modify: `api/app/routes/payments.py` — Apply rate limits
- Test: `api/tests/test_rate_limit.py`

**Limits:**
- `/api/auth/login`: 5 attempts per IP per minute
- `/api/auth/refresh`: 10 attempts per IP per minute
- `/api/payments/*`: 30 requests per IP per minute
- All other routes: 100 requests per IP per minute

**Implementation:**
- Use Redis as token bucket backend
- Return 429 Too Many Requests with `Retry-After` header
- Skip rate limiting for health endpoint

---

## Task 4: Audit Logging

**Goal:** Track all sensitive operations (payments, gate opens, manual overrides, settings changes) for compliance.

**Files:**
- Create: `api/app/models/audit_log.py` — AuditLog model
- Create: `api/app/services/audit.py` — Audit service
- Create: `api/app/routes/audit_logs.py` — Admin-only list endpoint
- Create: `api/alembic/versions/xxxx_add_audit_log.py` — Migration
- Test: `api/tests/test_audit_log.py`

**Schema:**
```
AuditLog: id, timestamp, user_id, action, entity_type, entity_id, details(JSON), ip_address, user_agent
```

**Tracked actions:**
- `CASH_PAYMENT`, `RFID_PAYMENT`, `EMONEY_PAYMENT`
- `MANUAL_GATE_OPEN`, `RESET_GATE`
- `SETTING_UPDATE`, `USER_CREATE`, `USER_UPDATE`
- `SETTLEMENT_TRIGGER`, `SETTLEMENT_UPLOAD`

---

## Task 5: Operations Runbook

**Goal:** Complete operations documentation for production deployment and daily operations.

**Files:**
- Create: `docs/OPERATIONS_RUNBOOK.md`
- Create: `docs/TROUBLESHOOTING.md`
- Create: `docs/DEPLOYMENT_GUIDE.md`

**Contents:**
- Deployment procedures (Docker, systemd)
- Daily operations (settlement upload, backup)
- Monitoring & alerting (Prometheus metrics, health checks)
- Troubleshooting guide (common issues, recovery procedures)
- Security checklist

---

## Task 6: Final Integration & Test Suite

**Goal:** Run full test suite, verify all tests pass, document any remaining issues.

**Commands:**
```bash
pytest -x -q                          # Full backend test suite
cd frontend && npm run build          # Frontend build verification
docker compose -f docker/docker-compose.prod.yml config  # Validate production config
```

**Expected:**
- All backend tests pass
- Frontend builds without errors
- No circular imports
- All routes load correctly

---

## Exit Criteria

| # | Criterion |
|---|-----------|
| 1 | RTSP snapshot worker captures frames from RTSP URLs |
| 2 | Lost-contact flow handles intermediate state correctly |
| 3 | Rate limiting returns 429 on excessive requests |
| 4 | Audit logs record all sensitive operations |
| 5 | Operations runbook covers deployment, monitoring, troubleshooting |
| 6 | All existing tests pass (no regressions) |
| 7 | New tests cover RTSP, recovery, rate limiting, audit logging |
| 8 | Frontend builds without errors |
| 9 | Documentation complete and accurate |

---

## Test Coverage Targets

| Component | New Tests |
|-----------|-----------|
| RTSP snapshot | 4 tests |
| Lost-contact recovery | 6 tests |
| Rate limiting | 5 tests |
| Audit logging | 4 tests |
| **Total new** | **19 tests** |
| **Total expected** | **~320 tests** |
