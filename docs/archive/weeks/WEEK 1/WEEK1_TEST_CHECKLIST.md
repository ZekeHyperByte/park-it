# Week 1 — Test Checklist

> **Date:** 25 April 2026
> **Goal:** Verify the foundation is solid before Week 2 begins.

---

## Pre-requisites

- [ ] Docker and Docker Compose installed
- [ ] Python 3.12+ available
- [ ] Virtual environment created: `python3 -m venv .venv && source .venv/bin/activate`
- [ ] Dependencies installed: `pip install -e ".[dev]"`

---

## Test 1: Docker Compose Infrastructure

**Command:**

```bash
docker compose up -d postgres redis
```

**Expected Result:**
- [x] `parking-postgres` container starts and shows `healthy`
- [x] `parking-redis` container starts and shows `healthy`
- [ ] PostgreSQL port 5432 is accessible
- [ ] Redis port 6379 is accessible

**Verify:**
```bash
docker compose ps
docker compose logs postgres --tail 5
docker compose logs redis --tail 5
```

---

## Test 2: Alembic Migration

**Command:**
```bash
alembic upgrade head
```

**Expected Result:**
- [ ] Migration runs without errors
- [x] `alembic_version` table exists with the latest revision

**Verify:**
```bash
docker compose exec -e PGPASSWORD=parking_secret postgres psql -U parking -d parking -c "SELECT * FROM alembic_version;"
```

---

## Test 3: Database Tables

**Command:**
```bash
docker compose exec -e PGPASSWORD=parking_secret postgres psql -U parking -d parking -c "\dt"
```

**Expected Result:**
- [x] All 21 tables exist:
  - `abandoned_vehicle_logs`
  - `alembic_version`
  - `area_parkir`
  - `emoney_readers`
  - `emoney_settlements`
  - `emoney_transactions`
  - `gate_ins`
  - `gate_outs`
  - `health_checks`
  - `manual_open_logs`
  - `member_groups`
  - `member_renewals`
  - `members`
  - `operator_alerts`
  - `parking_transactions`
  - `settings`
  - `shift_emoney_snapshots`
  - `shifts`
  - `snapshots`
  - `users`
  - `vehicle_types`

---

## Test 4: Critical Indexes

**Command:**
```bash
docker compose exec -e PGPASSWORD=parking_secret postgres psql -U parking -d parking -c "\di" | grep -E "(uq_active_card|idx_unsettled_emoney|idx_pending_correction)"
```

**Expected Result:**
- [x] `uq_active_card` on `parking_transactions`
- [x] `idx_unsettled_emoney` on `emoney_transactions`
- [x] `idx_pending_correction` on `emoney_transactions`

---

## Test 5: Seed Script

**Command:**
```bash
python scripts/seed.py
```

**Expected Result:**
- [ ] Script completes without errors
- [ ] 2 users created (admin, operator)
- [ ] 3 vehicle types created (Motor, Mobil, Bus)
- [ ] 1 area parkir created
- [ ] 3 shifts created (Pagi, Sore, Malam)
- [ ] 1 member group created
- [ ] 1 member created
- [ ] 1 gate-in created
- [ ] 1 gate-out created

**Verify:**
```bash
docker compose exec -e PGPASSWORD=parking_secret postgres psql -U parking -d parking -c "SELECT id, username, role FROM users;"
docker compose exec -e PGPASSWORD=parking_secret postgres psql -U parking -d parking -c "SELECT name, code FROM vehicle_types;"
docker compose exec -e PGPASSWORD=parking_secret postgres psql -U parking -d parking -c "SELECT name, gate_mode FROM gate_ins;"
```

---

## Test 6: FastAPI Application

**Command:**
```bash
uvicorn api.app.main:app --host 0.0.0.0 --port 8000
```

**Expected Result:**
- [ ] Server starts without errors
- [ ] Logs show `api_starting` with app name
- [ ] Logs show `api_config_loaded` with env and debug

**Verify Health Endpoint:**
```bash
curl http://localhost:8000/api/health
```

**Expected Response:**
```json
{"status": "ok"}
```

---

## Test 7: Model Imports

**Command:**
```bash
python -c "from api.app.models import *; print('All models imported successfully')"
```

**Expected Result:**
- [ ] All 21 models import without errors
- [ ] No circular import errors

---

## Test 8: Shared Layer Imports

**Command:**
```bash
python -c "from shared.config import get_settings; s = get_settings(); print('DB URL:', s.database_url)"
python -c "from shared.logging import configure_logging, get_logger; configure_logging(); get_logger().info('test')"
python -c "from shared.events import PaymentMethod, DeductResultEvent, OpenGateCommand; print('events OK')"
python -c "from shared.redis import redis_client; print('redis OK')"
```

**Expected Result:**
- [ ] Config loads correctly with database_url
- [ ] Logging configures and outputs to console
- [ ] Events module imports all message types
- [ ] Redis client module imports

---

## Test 9: Docker Compose Build (API)

**Command:**
```bash
docker compose build api
```

**Expected Result:**
- [ ] Docker image builds without errors
- [ ] All Python dependencies install cleanly

---

## Test 10: API Service with Docker Compose

**Command:**
```bash
docker compose up -d api
curl http://localhost:8000/api/health
```

**Expected Result:**
- [ ] API container starts and responds
- [ ] Health endpoint returns `{"status":"ok"}`

---

## Week 1 Exit Criteria Summary

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `docker compose up --build -d` succeeds without errors | ⬜ |
| 2 | All 5 services running: api, postgres, pgbouncer, redis | ⬜ |
| 3 | `alembic upgrade head` creates all tables + indexes + constraints | ⬜ |
| 4 | `python scripts/seed.py` populates dev data successfully | ⬜ |
| 5 | `curl http://localhost:8000/api/health` returns `{"status":"ok"}` | ⬜ |
| 6 | All model files import without errors | ⬜ |
| 7 | shared/ layer imports without errors | ⬜ |
| 8 | No circular imports between layers | ⬜ |
| 9 | `.gitignore` excludes `parking-system/` | ⬜ |
| 10 | All changes committed to git | ⬜ |

> **Note:** Mark each checkbox as ✅ after manually running the test and confirming success.

---

## Known Issues / Notes

1. **Circular FKs removed:** `ParkingTransaction.emoney_transaction_id`, `entry_snapshot_id`, `exit_snapshot_id` and `Snapshot.parking_transaction_id` do not have database-level FK constraints to avoid circular dependency issues in Alembic. These relationships are enforced at the application layer.

2. **passlib bcrypt compatibility:** The seed script uses `bcrypt` directly instead of `passlib` due to a compatibility issue with newer `bcrypt` versions (72-byte limit during backend detection). This will be addressed in Week 2 when implementing the auth layer.

3. **Docker Compose version warning:** The `version` attribute in `docker-compose.yml` is obsolete in newer Docker Compose versions but harmless.
