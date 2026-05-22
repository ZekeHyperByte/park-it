# Week 2 — Test Checklist

> **Date:** 25 April 2026
> **Goal:** Verify auth, API, WebSocket, workers, and protocol layer

---

## Pre-requisites

- [x] Week 1 exit criteria all passed
- [x] Docker Compose running (postgres, redis)
- [x] Dependencies installed: `pip install -e ".[dev]"`
- [x] `.env` configured with JWT_SECRET

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| T1: Password hashing utility | **PASS** | 5/5 tests |
| T2: JWT token lifecycle | **PASS** | 6/6 tests |
| T3: Auth service | **PASS** | 6/6 tests |
| T4: Tariff calculation | **PASS** | 10/10 tests |
| T5: PASSTI frame builder | **PASS** | 8/8 tests |
| T6: Compass STAT parser | **PASS** | 13/13 tests |
| T7: Alembic migration | **PASS** | Applied to dev DB |
| T8: FastAPI app loading | **PASS** | All routes mounted |
| **Total** | **47/47** | **100%** |

---

## Detailed Test Log

### T1: Password Hashing
```bash
pytest api/tests/test_password.py -v
```
- [x] Hash generates in < 500ms
- [x] Verification returns True for correct password
- [x] Verification returns False for wrong password
- [x] Different passwords produce different hashes
- [x] Unicode passwords work correctly

### T2: JWT Token Lifecycle
```bash
pytest api/tests/test_jwt.py -v
```
- [x] Access token creates with 30min expiry
- [x] Refresh token creates with 7d expiry
- [x] Decode returns correct claims
- [x] Expired token raises exception
- [x] Access and refresh tokens are different
- [x] Token types correctly labeled

### T3: Auth Service
```bash
pytest api/tests/test_auth_service.py -v
```
- [x] authenticate_user returns tokens for valid credentials
- [x] Returns None for invalid username
- [x] Returns None for wrong password
- [x] Returns None for inactive user
- [x] create_tokens generates both access and refresh
- [x] Tokens contain correct user claims

### T4: Tariff Calculation
```bash
pytest api/tests/test_tariff.py -v
```
- [x] Grace period (15 min) = 0 fee
- [x] One hour = hourly rate
- [x] Partial hour rounds up
- [x] Daily cap respected
- [x] Motor rate lower than mobil
- [x] Bus rate higher than mobil
- [x] Exit before entry raises ValueError
- [x] Unknown vehicle type raises ValueError
- [x] Custom config works

### T5: PASSTI Frame Protocol
```bash
pytest protocols/tests/test_passti_frame.py -v
```
- [x] Frame starts with STX (0x02)
- [x] Length bytes correct
- [x] Payload starts with EF 01 CMD
- [x] LRC checksum validates
- [x] Success response parses correctly
- [x] Error response parses correctly (status 01 10 04)
- [x] Too short response handled
- [x] Invalid STX handled

### T6: Compass Parser
```bash
pytest protocols/tests/test_compass_parser.py -v
```
- [x] Empty response has no inputs
- [x] IN2 ON detected
- [x] IN1 ON detected
- [x] Wiegand W (RFID) parsed
- [x] Wiegand X (UHF) parsed
- [x] Multiple inputs active
- [x] STAT1 format for IN2
- [x] STAT10 format for IN1
- [x] No card returns None
- [x] RFID card detected
- [x] UHF card detected
- [x] RFID takes priority over UHF

### T7: Alembic Migration
```bash
alembic upgrade head
```
- [x] Migration generates without errors
- [x] `emoney_readers.connection_type` column exists
- [x] `gate_ins.relay_mode` column exists
- [x] `gate_outs.relay_mode` column exists
- [x] Existing rows updated with defaults

### T8: FastAPI Application
```bash
python -c "from api.app.main import app; print([r.path for r in app.routes])"
```
- [x] App loads without errors
- [x] All routes visible:
  - `/api/health`
  - `/api/auth/login`, `/api/auth/logout`, `/api/auth/refresh`, `/api/auth/me`
  - `/api/users`
  - `/api/gates/in`, `/api/gates/out`
  - `/api/settings`
  - `/ws/{gate_id}`
- [x] No circular imports

---

## Manual Verification Steps (Not Automated)

The following require manual testing or integration with external services:

| Step | Command | Expected |
|------|---------|----------|
| Login endpoint | `curl -X POST http://localhost:8000/api/auth/login -d '{"username":"admin","password":"admin123"}' -H "Content-Type: application/json"` | HTTP 200 + 2 Set-Cookie headers |
| Me endpoint | `curl http://localhost:8000/api/auth/me -H "Cookie: access_token=..."` | HTTP 200 + user JSON |
| Logout endpoint | `curl -X POST http://localhost:8000/api/auth/logout -H "Cookie: access_token=..."` | HTTP 200 + cookies cleared |
| WS connection | `websocat ws://localhost:8000/ws/gate-in-1 -H="Cookie: access_token=..."` | 101 Switching Protocols |
| ARQ critical worker | `arq workers.settings.CriticalWorkerSettings` | Starts without errors |
| ARQ background worker | `arq workers.settings.BackgroundWorkerSettings` | Starts without errors |
| Telegram alert | Enqueue `send_telegram_alert` job with chat_id | Message delivered to Telegram |

---

## Known Issues / Notes

1. **JWT secret length warning:** PyJWT warns about the default dev secret being < 32 bytes. Production must use a 64+ character random string.

2. **WebSocket broadcaster:** The Redis pub/sub broadcaster starts with the FastAPI lifespan. In multi-worker Gunicorn setup, each worker will have its own broadcaster instance, which is correct — all workers subscribe to Redis and broadcast to their local WS connections.

3. **Camera snapshots:** The snapshot worker downloads images via HTTP. For RTSP cameras without HTTP snapshot URL, a proxy sidecar is needed (Week 4).

4. **Telegram bot token:** The bot token is stored in `workers/background/notification_worker.py`. In production, this should be moved to environment variables.

5. **Test database:** Tests use `parking_test` database. The conftest.py creates and drops tables for each test function to ensure isolation.

---

*End of Week 2 Test Checklist*
