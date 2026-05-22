# Week 7 — System Hardening & Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden the system with comprehensive tests, frontend polish, Redis caching, integration tests, and production deployment configuration.

**Architecture:** Build on Weeks 1–6 foundation. Add tests for all Week 6 CRUD routes, fix frontend UX issues, implement Redis caching for reference data, write daemon+API integration tests, and create deployment artifacts.

**Tech Stack:** FastAPI, SQLAlchemy async, pytest, Nuxt 3, Element Plus, Redis, systemd, nginx, Docker

---

## Task 1: Backend CRUD Route Tests

**Files:**
- Create: `api/tests/test_vehicle_type_routes.py`
- Create: `api/tests/test_shift_routes.py`
- Create: `api/tests/test_area_routes.py`
- Create: `api/tests/test_emoney_reader_routes.py`
- Create: `api/tests/test_member_routes.py`
- Create: `api/tests/test_member_group_routes.py`
- Create: `api/tests/test_transaction_routes.py`
- Create: `api/tests/test_manual_open_log_routes.py`
- Create: `api/tests/test_abandoned_vehicle_routes.py`
- Create: `api/tests/test_report_routes.py`
- Modify: `api/tests/conftest.py` (if needed for fixtures)

**Step 1: Write test fixtures**

Add fixtures for vehicle_type, shift, area, emoney_reader, member, member_group in the test conftest.

**Step 2: Write vehicle type route tests**

Test GET /api/vehicle-types (list), POST (create), PATCH (update), DELETE.
Verify admin-only access (403 for operator).

Run: `pytest api/tests/test_vehicle_type_routes.py -v`
Expected: 6–8 tests PASS

**Step 3: Write shift route tests**

Same pattern for /api/shifts.

Run: `pytest api/tests/test_shift_routes.py -v`
Expected: 6–8 tests PASS

**Step 4: Write area route tests**

Same pattern for /api/areas.

Run: `pytest api/tests/test_area_routes.py -v`
Expected: 6–8 tests PASS

**Step 5: Write emoney reader route tests**

Same pattern for /api/emoney-readers.

Run: `pytest api/tests/test_emoney_reader_routes.py -v`
Expected: 6–8 tests PASS

**Step 6: Write member route tests**

Test /api/members and /api/member-groups.

Run: `pytest api/tests/test_member_routes.py api/tests/test_member_group_routes.py -v`
Expected: 10–12 tests PASS

**Step 7: Write transaction route tests**

Test /api/transactions list with filters, /api/transactions/{id} detail.

Run: `pytest api/tests/test_transaction_routes.py -v`
Expected: 4–6 tests PASS

**Step 8: Write log route tests**

Test /api/manual-open-logs and /api/abandoned-vehicle-logs.

Run: `pytest api/tests/test_manual_open_log_routes.py api/tests/test_abandoned_vehicle_routes.py -v`
Expected: 4–6 tests PASS

**Step 9: Write report route tests**

Test /api/reports/summary and /api/reports/emoney with seeded transactions.

Run: `pytest api/tests/test_report_routes.py -v`
Expected: 4–6 tests PASS

**Step 10: Run full backend test suite**

Run: `pytest -x -q`
Expected: All tests PASS (190 + ~50 new = ~240)

**Step 11: Commit**

```bash
git add api/tests/
git commit -m "test(week7): add comprehensive CRUD route tests for all Week 6 endpoints"
```

---

## Task 2: Frontend Hardening

**Files:**
- Modify: `frontend/pages/member.vue`
- Modify: `frontend/pages/transaksi.vue`
- Modify: `frontend/pages/report.vue`
- Modify: `frontend/components/CrudModal.vue`
- Modify: `api/app/routes/manual_open_logs.py`
- Modify: `api/app/routes/abandoned_vehicles.py`
- Modify: `api/app/schemas/manual_open_log.py` (create)
- Modify: `api/app/schemas/abandoned_vehicle.py` (create)

**Step 1: Add select/dropdown field type to CrudModal**

In `CrudModal.vue`, add a new field type `select` that renders `el-select` with options.
Options passed via field schema: `{ type: 'select', options: [{label, value}] }`.

**Step 2: Fix member form with dropdowns**

In `member.vue`, fetch `/api/vehicle-types` and `/api/member-groups` on mount.
Pass options to CrudModal for `vehicle_type_id` and `member_group_id` fields.

Run: `cd frontend && npm run build`
Expected: Build succeeds, no errors.

**Step 3: Add date picker field type to CrudModal**

Add `date` field type that renders `el-date-picker` with `value-format="YYYY-MM-DD"`.

**Step 4: Fix member validity dates**

Change `valid_from` and `valid_until` fields in member form from text to date picker.

Run: `cd frontend && npm run build`
Expected: Build succeeds.

**Step 5: Add default date range to report page**

In `report.vue`, set default `date_from` to start of current month, `date_to` to today.

**Step 6: Enable server-side pagination for transactions**

In `api/app/routes/transactions.py`, ensure `skip` and `limit` query params are applied.
In `transaksi.vue`, pass `page` and `pageSize` to API and handle total count.

**Step 7: Enrich manual open log responses**

Create `ManualOpenLogListItem` schema with `operator_name`, `gate_name`.
Update route to join with User and GateOut tables.

**Step 8: Enrich abandoned vehicle log responses**

Create `AbandonedVehicleLogListItem` schema with `gate_name`.
Update route to join with GateOut table.

**Step 9: Frontend build verification**

Run: `cd frontend && npm run build`
Expected: Build succeeds, 0 errors.

**Step 10: Commit**

```bash
git add frontend/ api/app/routes/ api/app/schemas/
git commit -m "feat(week7): frontend hardening — dropdowns, date pickers, server pagination, enriched log responses"
```

---

## Task 3: Redis Caching Layer

**Files:**
- Modify: `shared/redis.py`
- Create: `api/app/cache/__init__.py`
- Create: `api/app/cache/reference_data.py`
- Modify: `api/app/routes/gates.py`
- Modify: `api/app/routes/settings.py`
- Modify: `api/app/routes/vehicle_types.py`
- Modify: `api/app/routes/members.py`
- Modify: `api/app/services/member.py` (if exists, else create)

**Step 1: Add cache helper methods to shared/redis.py**

Add:
- `cache_set(key, value, ttl=300)` — JSON serialize + Redis SETEX
- `cache_get(key)` — JSON deserialize + Redis GET
- `cache_delete(key)` — Redis DEL
- `cache_delete_pattern(pattern)` — Redis KEYS + DEL

**Step 2: Create reference data cache module**

In `api/app/cache/reference_data.py`, create functions:
- `get_cached_gate_ins()` / `invalidate_gate_ins()`
- `get_cached_gate_outs()` / `invalidate_gate_outs()`
- `get_cached_vehicle_types()` / `invalidate_vehicle_types()`
- `get_cached_members()` / `invalidate_members()`
- `get_cached_settings()` / `invalidate_settings()`

Each uses Redis with 5-minute TTL.

**Step 3: Integrate cache into read routes**

Modify `gates.py`, `settings.py`, `vehicle_types.py`, `members.py` list endpoints:
1. Check cache first
2. If miss, query DB, store in cache, return

**Step 4: Add cache invalidation on write operations**

On POST/PATCH/DELETE in the same routes, call invalidate function.

**Step 5: Write cache tests**

Create `api/tests/test_cache.py` with tests for:
- Cache hit returns data without DB query
- Cache miss queries DB and populates cache
- Write invalidates cache
- TTL expiry

Run: `pytest api/tests/test_cache.py -v`
Expected: 4–6 tests PASS

**Step 6: Run full test suite**

Run: `pytest -x -q`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add shared/redis.py api/app/cache/ api/app/routes/
git commit -m "feat(week7): Redis caching layer for reference data with TTL and invalidation"
```

---

## Task 4: Integration Tests

**Files:**
- Create: `api/tests/test_integration_daemon_api.py`
- Modify: `daemons/tests/conftest.py` (share FakeRedis if possible)

**Step 1: Create integration test for command flow**

Test: FastAPI publishes `open_gate` command → Redis Stream → Daemon consumes → publishes `gate_opened` event → FastAPI WebSocket receives.

Use FakeRedis or real Redis (docker-compose redis service).

**Step 2: Create integration test for payment flow**

Test: Full cash payment flow:
1. Create active transaction
2. Call `POST /api/payments/cash`
3. Verify command published to Redis Stream
4. Verify transaction updated in DB

**Step 3: Run integration tests**

Run: `pytest api/tests/test_integration_daemon_api.py -v`
Expected: 4–6 tests PASS

**Step 4: Commit**

```bash
git add api/tests/test_integration_daemon_api.py
git commit -m "test(week7): integration tests for daemon-API command and payment flows"
```

---

## Task 5: Deployment Configuration

**Files:**
- Create: `docker/docker-compose.prod.yml`
- Create: `docker/nginx.conf`
- Create: `systemd/parking-api.service`
- Create: `systemd/parking-worker-critical.service`
- Create: `systemd/parking-worker-bg.service`
- Create: `systemd/parking-daemon-gate-in@.service`
- Create: `systemd/parking-daemon-gate-out@.service`
- Create: `scripts/deploy.sh`
- Create: `docs/WEEK 7/WEEK7_DEPLOYMENT.md`

**Step 1: Production Docker Compose**

Create `docker-compose.prod.yml` with:
- postgres (volume-mounted, restart always)
- redis (restart always)
- api (gunicorn, restart always, healthcheck)
- worker-critical (arq, restart always)
- worker-bg (arq, restart always)

**Step 2: Nginx configuration**

Create `nginx.conf` with:
- Reverse proxy to FastAPI on /api/
- WebSocket upgrade on /ws/
- Static files for frontend build output
- proxy_read_timeout 3600s for WS

**Step 3: systemd service files**

Create service files per development plan:
- parking-api (gunicorn)
- parking-worker-critical (arq)
- parking-worker-bg (arq)
- parking-daemon-gate-in@{id} (template for multiple gates)
- parking-daemon-gate-out@{id} (template for multiple gates)

All run as `parking` user, `dialout` group.

**Step 4: Deployment script**

Create `scripts/deploy.sh` that:
- Builds frontend
- Copies nginx config
- Reloads systemd
- Starts/restarts services
- Runs health checks

**Step 5: Commit**

```bash
git add docker/ systemd/ scripts/deploy.sh
git commit -m "feat(week7): production deployment configuration — docker, nginx, systemd"
```

---

## Task 6: Final Verification & Documentation

**Step 1: Run full backend test suite**

Run: `pytest -x -q`
Expected: ALL tests pass

**Step 2: Frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds, 0 errors

**Step 3: Circular import check**

Run: `python -c "from api.app.main import app; print('OK')"`
Expected: OK

**Step 4: FastAPI route count**

Run: `python -c "from api.app.main import app; print(len([r for r in app.routes if hasattr(r,'path')]))"`
Expected: 66 routes loaded

**Step 5: Write Week 7 build log**

Create `docs/WEEK 7/WEEK7_CHANGES.md`
Create `docs/WEEK 7/WEEK7_TEST_CHECKLIST.md`

**Step 6: Update development plan**

If any locked decisions changed, update `docs/EParking_v2_Development_Plan.md`.

**Step 7: Final commit**

```bash
git add docs/
git commit -m "docs(week7): Week 7 build log, test checklist, and deployment docs"
```

---

## Exit Criteria

| # | Criterion | Target |
|---|---|---|
| 1 | All backend tests pass | 240+ tests |
| 2 | Frontend builds without errors | ✅ |
| 3 | No circular imports | ✅ |
| 4 | All 66 FastAPI routes load | ✅ |
| 5 | Redis caching works (tests prove it) | ✅ |
| 6 | Integration tests pass | ✅ |
| 7 | Deployment configs created | ✅ |
| 8 | Week 7 documentation complete | ✅ |
