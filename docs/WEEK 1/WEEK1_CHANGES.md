# Week 1 — Changes & Build Log

> **Date:** 25 April 2026
> **Scope:** Foundation & Database

---

## What Was Built

### 1. Project Skeleton

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python package config, dependencies, tool settings (ruff, mypy, pytest) |
| `docker-compose.yml` | 4 services: postgres, pgbouncer, redis, api |
| `docker/Dockerfile.api` | FastAPI container image |
| `docker/postgres-init.sql` | PostgreSQL extensions setup |
| `.env.example` | All required environment variables documented |
| `.gitignore` | Standard ignores + `parking-system/` exclusion |
| `README.md` | Quick start guide |

### 2. Shared Layer (`shared/`)

| File | Purpose |
|------|---------|
| `shared/config.py` | pydantic-settings with env var loading, database/redis URL builders |
| `shared/logging.py` | structlog configuration (JSON for prod, colored console for dev), trace_id support |
| `shared/redis.py` | Async Redis client singleton with Streams + Pub/Sub + cache helpers |
| `shared/events.py` | All Redis IPC message schemas (Pydantic): 13 event types, 13 command types |

### 3. FastAPI Factory (`api/app/`)

| File | Purpose |
|------|---------|
| `api/app/main.py` | FastAPI app factory with lifespan manager, CORS, router mounting |
| `api/app/routes/health.py` | GET /api/health — returns `{"status": "ok"}` |

### 4. Database Layer (`api/app/models/`)

| File | Model | Type |
|------|-------|------|
| `base.py` | Base, TimestampMixin, IntPKMixin | Base classes |
| `user.py` | User | V1 baseline |
| `vehicle_type.py` | VehicleType | V1 baseline |
| `area_parkir.py` | AreaParkir | V1 baseline |
| `shift.py` | Shift | V1 baseline |
| `member_group.py` | MemberGroup | V1 baseline |
| `member.py` | Member | V1 baseline |
| `member_renewal.py` | MemberRenewal | V1 baseline |
| `snapshot.py` | Snapshot | V1 baseline (modified: removed circular FK) |
| `manual_open_log.py` | ManualOpenLog | V1 baseline |
| `gate_in.py` | GateIn | V1 baseline + V2 additions (gate_mode, emoney settings, hardware config) |
| `gate_out.py` | GateOut | V1 baseline + V2 additions (emoney_reader_id, payment_timeout, hardware config) |
| `parking_transaction.py` | ParkingTransaction | V1 baseline + V2 additions (payment_method, member_id, emoney_transaction_id) |
| `emoney_reader.py` | EmoneyReader | V2 NEW |
| `emoney_transaction.py` | EmoneyTransaction | V2 NEW |
| `emoney_settlement.py` | EmoneySettlement | V2 NEW |
| `shift_emoney_snapshot.py` | ShiftEmoneySnapshot | V2 NEW |
| `abandoned_vehicle_log.py` | AbandonedVehicleLog | V2 NEW |
| `operator_alert.py` | OperatorAlert | V2 NEW |
| `health_check.py` | HealthCheck | V2 NEW |
| `setting.py` | Setting | V1 baseline |

**Key Constraints & Indexes:**
- `uq_active_card`: Partial unique index on `parking_transactions(card_number)` WHERE status='ACTIVE'
- `idx_unsettled_emoney`: Partial index on `emoney_transactions(created_at)` WHERE unsettled + SUCCESS
- `idx_pending_correction`: Partial index on `emoney_transactions(created_at)` WHERE LOST_CONTACT or CORRECTION_FAILED

### 5. Alembic Setup (`api/alembic/`)

| File | Purpose |
|------|---------|
| `alembic.ini` | Alembic configuration |
| `api/alembic/env.py` | Async Alembic environment with autogenerate support |
| `api/alembic/script.py.mako` | Migration template |
| `api/alembic/versions/914e5fe1c754_initial_schema.py` | Initial migration (all 21 tables + indexes) |

### 6. Seed Script (`scripts/seed.py`)

- Creates test admin + operator users
- Creates 3 vehicle types (Motor, Mobil, Bus)
- Creates 1 parking area
- Creates 3 shifts (Pagi, Sore, Malam)
- Creates 1 member group + 1 member
- Creates 1 gate-in + 1 gate-out with sample hardware config

---

## Verification Results

| Test | Result |
|------|--------|
| Docker Compose (postgres + redis) | ✅ Healthy |
| Alembic migration | ✅ Applied successfully |
| All 21 tables created | ✅ Verified |
| Critical indexes exist | ✅ Verified |
| Seed script | ✅ Populated dev data |
| FastAPI health endpoint | ✅ Returns `{"status":"ok"}` |
| Model imports | ✅ All 21 models |
| Shared layer imports | ✅ Config, logging, events, redis |

---

## Decisions Made

1. **Removed circular FK constraints:** `ParkingTransaction.emoney_transaction_id`, `entry_snapshot_id`, `exit_snapshot_id` and `Snapshot.parking_transaction_id` have no database-level FK constraints. This avoids Alembic circular dependency issues. Relationships are maintained at the application layer.

2. **Used `bcrypt` directly in seed script:** passlib's bcrypt handler has compatibility issues with bcrypt >= 4.0. Auth layer in Week 2 will use a proper password hashing strategy.

3. **BigInteger primary keys:** All tables use `BigInteger` with `autoincrement=True` for consistency with v1's likely auto-increment IDs.

4. **Kept Docker Compose `version`:** Left in for compatibility with older Docker Compose versions, even though it's obsolete in v2.

---

## Files Created/Modified

**Created:** 35+ new files across `api/`, `shared/`, `scripts/`, `docker/`, `docs/`

**Modified:** None (greenfield Week 1)

**Total lines of code:** ~2,500+
