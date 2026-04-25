# Week 1 — Foundation & Database Implementation Plan

> **Goal:** Scaffold the entire v2 monorepo with Docker Compose, shared layer, FastAPI factory, all SQLAlchemy async models, Alembic migrations, and seed data.

**Architecture:** Clean monorepo with strict dependency contracts. FastAPI async app with SQLAlchemy 2.0 async ORM. PostgreSQL 16 + pgBouncer + Redis 7 via Docker Compose. All configuration via pydantic-settings.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic (async), PostgreSQL 16, Redis 7, pgBouncer, pydantic-settings, structlog, uvicorn, gunicorn

---

## Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `docker/postgres-init.sql`

**Step 1: Write pyproject.toml**

Dependencies: fastapi, uvicorn[standard], gunicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic, pydantic-settings, PyJWT[crypto], passlib[bcrypt], redis, arq, httpx, structlog, pyserial, python-escpos, cryptography

**Step 2: Write docker-compose.yml**

Services: api (FastAPI), postgres (PostgreSQL 16), pgbouncer, redis

**Step 3: Write .env.example**

All required env vars for DB, Redis, JWT, etc.

**Step 4: Write .gitignore**

Standard Python + Node + IDE ignores + `parking-system/`

**Step 5: Write docker/postgres-init.sql**

Create `parking` database on init.

**Step 6: Commit**

```bash
git add pyproject.toml docker-compose.yml .env.example .gitignore docker/
git commit -m "chore: project skeleton + docker compose"
```

---

## Task 2: Shared Layer

**Files:**
- Create: `shared/config.py`
- Create: `shared/logging.py`
- Create: `shared/redis.py`
- Create: `shared/events.py`
- Create: `shared/__init__.py`

**Step 1: Write shared/config.py**

Pydantic-settings with env vars for DB, Redis, JWT secret, etc.

**Step 2: Write shared/logging.py**

structlog configuration with JSON renderer for production, console renderer for dev. Trace ID binding support.

**Step 3: Write shared/redis.py**

Redis client singleton with async connection. Helper methods for Streams XADD/XREADGROUP and Pub/Sub PUBLISH.

**Step 4: Write shared/events.py**

Pydantic models for all Redis messages (commands and events) as documented in the plan.

**Step 5: Commit**

```bash
git add shared/
git commit -m "feat: shared layer — config, logging, redis, events"
```

---

## Task 3: FastAPI Factory

**Files:**
- Create: `api/app/main.py`
- Create: `api/app/middleware/__init__.py`
- Create: `api/app/middleware/cors.py`
- Create: `api/app/routes/__init__.py`
- Create: `api/app/routes/health.py`
- Create: `api/__init__.py`
- Create: `api/app/__init__.py`

**Step 1: Write api/app/main.py**

FastAPI factory with lifespan context manager. Mount health router. Include CORS middleware.

**Step 2: Write api/app/routes/health.py**

GET /api/health — returns {"status": "ok"}

**Step 3: Commit**

```bash
git add api/
git commit -m "feat: fastapi factory + health endpoint"
```

---

## Task 4: Database Layer — Models

**Files:**
- Create: `api/database.py`
- Create: `api/app/models/__init__.py`
- Create: `api/app/models/base.py`
- Create: `api/app/models/user.py`
- Create: `api/app/models/vehicle_type.py`
- Create: `api/app/models/area_parkir.py`
- Create: `api/app/models/gate_in.py`
- Create: `api/app/models/gate_out.py`
- Create: `api/app/models/parking_transaction.py`
- Create: `api/app/models/emoney_transaction.py`
- Create: `api/app/models/emoney_settlement.py`
- Create: `api/app/models/emoney_reader.py`
- Create: `api/app/models/shift.py`
- Create: `api/app/models/shift_emoney_snapshot.py`
- Create: `api/app/models/abandoned_vehicle_log.py`
- Create: `api/app/models/setting.py`
- Create: `api/app/models/operator_alert.py`
- Create: `api/app/models/health_check.py`
- Create: `api/app/models/snapshot.py`
- Create: `api/app/models/manual_open_log.py`
- Create: `api/app/models/member.py`
- Create: `api/app/models/member_group.py`
- Create: `api/app/models/member_renewal.py`

**Step 1: Write api/database.py**

Async SQLAlchemy engine + async sessionmaker. get_db() dependency for FastAPI.

**Step 2: Write api/app/models/base.py**

DeclarativeBase with common columns: id (UUID or BIGINT), created_at, updated_at.

**Step 3: Write all model files**

Implement ALL models per the development plan:
- V1 baseline models: User, VehicleType, AreaParkir, GateIn, GateOut, ParkingTransaction, Shift, Snapshot, ManualOpenLog, Member, MemberGroup, MemberRenewal, Setting
- V2 new models: EmoneyTransaction, EmoneySettlement, EmoneyReader, ShiftEmoneySnapshot, AbandonedVehicleLog, OperatorAlert, HealthCheck
- V2 modified models: ParkingTransaction (+payment_method, member_id FK, emoney_transaction_id FK), GateIn (+gate_mode, emoney_minimum_balance, etc.), GateOut (+emoney_reader_id FK, payment_timeout_seconds, etc.), Setting (+emoney defaults, settlement config)

Include all indexes and constraints:
- Partial unique index on parking_transactions(card_number) WHERE status='active'
- Partial index on emoney_transactions for unsettled
- Partial index on emoney_transactions for pending correction

**Step 4: Verify models import cleanly**

Run: `python -c "from api.app.models import *"`

**Step 5: Commit**

```bash
git add api/database.py api/app/models/
git commit -m "feat: all sqlalchemy async models with indexes and constraints"
```

---

## Task 5: Alembic Setup

**Files:**
- Create: `alembic.ini`
- Create: `api/alembic/env.py`
- Create: `api/alembic/script.py.mako`
- Create: `api/alembic/versions/.gitkeep`
- Create: `api/alembic/README`

**Step 1: Configure alembic.ini**

Async SQLAlchemy URL pattern. Script location = api/alembic.

**Step 2: Write api/alembic/env.py**

Async Alembic environment. Import all models for autogenerate.

**Step 3: Generate initial migration**

Run: `alembic revision --autogenerate -m "initial schema"`

**Step 4: Verify migration on fresh DB**

Run: `docker compose up -d postgres pgbouncer redis`
Run: `alembic upgrade head`
Verify: Connect to DB, confirm all tables exist.

**Step 5: Commit**

```bash
git add alembic.ini api/alembic/
git commit -m "feat: alembic async setup + initial migration"
```

---

## Task 6: Seed Script

**Files:**
- Create: `scripts/seed.py`
- Create: `scripts/__init__.py`

**Step 1: Write scripts/seed.py**

Async seed script that:
- Creates test admin user (password hashed with bcrypt)
- Creates sample vehicle types (Motor, Mobil, Bus, Truk)
- Creates sample area parkir
- Creates sample gates (1 gate-in, 1 gate-out)
- Creates sample tariff rules
- Creates sample shifts

**Step 2: Test seed script**

Run: `python scripts/seed.py`
Verify: Query DB for seeded data.

**Step 3: Commit**

```bash
git add scripts/
git commit -m "feat: dev seed script"
```

---

## Task 7: Week 1 Verification & Documentation

**Files:**
- Create: `docs/WEEK1_TEST_CHECKLIST.md`
- Create: `docs/WEEK1_CHANGES.md`

**Step 1: Write WEEK1_TEST_CHECKLIST.md**

Comprehensive checklist for manual verification.

**Step 2: Write WEEK1_CHANGES.md**

Summary of all changes made in Week 1.

**Step 3: Run final verification**

Run: `docker compose up --build -d`
Run: `docker compose logs api`
Expected: All services healthy, FastAPI responding.

**Step 4: Commit**

```bash
git add docs/WEEK1_TEST_CHECKLIST.md docs/WEEK1_CHANGES.md
git commit -m "docs: week 1 test checklist and change log"
```

---

## Test Commands Summary

```bash
# 1. Build and start infrastructure
docker compose up --build -d

# 2. Check service health
docker compose ps
docker compose logs api
docker compose logs postgres

# 3. Run Alembic migration
cd /home/qiu/Work/E-Parking/parking-system-v2
python -m alembic upgrade head

# 4. Run seed script
python scripts/seed.py

# 5. Test health endpoint
curl http://localhost:8000/api/health

# 6. Verify DB tables
docker compose exec postgres psql -U parking -d parking -c "\dt"

# 7. Verify indexes
docker compose exec postgres psql -U parking -d parking -c "\di"

# 8. Verify seed data
docker compose exec postgres psql -U parking -d parking -c "SELECT * FROM users;"
```

---

## Week 1 Exit Criteria

- [ ] `docker compose up --build -d` succeeds without errors
- [ ] All 5 services running: api, postgres, pgbouncer, redis
- [ ] `alembic upgrade head` creates all tables + indexes + constraints
- [ ] `python scripts/seed.py` populates dev data successfully
- [ ] `curl http://localhost:8000/api/health` returns `{"status":"ok"}`
- [ ] All model files import without errors
- [ ] shared/ layer imports without errors
- [ ] No circular imports between layers
- [ ] `.gitignore` excludes `parking-system/`
- [ ] All changes committed to git
