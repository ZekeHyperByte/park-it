# WEEK 7 — System Hardening & Polish

## Summary

Week 7 focused on production readiness: comprehensive test coverage, frontend UX improvements, Redis caching for performance, integration tests for the FastAPI-to-Daemon message bus, and deployment configuration files.

---

## Task 1: Backend CRUD Route Tests

### What Changed
- Added **10 new test files** covering all Week 6 CRUD endpoints:
  - `api/tests/test_vehicle_types_routes.py`
  - `api/tests/test_shifts_routes.py`
  - `api/tests/test_areas_routes.py`
  - `api/tests/test_emoney_readers_routes.py`
  - `api/tests/test_member_groups_routes.py`
  - `api/tests/test_members_routes.py`
  - `api/tests/test_transactions_routes.py`
  - `api/tests/test_manual_open_logs_routes.py`
  - `api/tests/test_abandoned_vehicles_routes.py`
  - `api/tests/test_reports_routes.py`

### Key Patterns
- `app.dependency_overrides` used to mock `require_auth` dependency
- Mock `Request` objects must be explicitly type-annotated to avoid FastAPI treating them as query parameters (422 errors)
- All tests use async `AsyncClient` from `httpx`

### Results
- **79 new backend tests** added
- All pass in ~85 seconds

---

## Task 2: Frontend Hardening

### What Changed

#### CrudModal.vue
- Added `date` field type support using `<el-date-picker>`
- Date fields support `value-format="YYYY-MM-DD"` for clean API serialization

#### Member Management (`pages/member.vue`)
- **Vehicle type dropdown**: `el-select` populated from `/vehicle_types` API
- **Member group dropdown**: `el-select` populated from `/member_groups` API
- **Date pickers**: `valid_from` / `valid_until` using `el-date-picker` with `YYYY-MM-DD` format
- Removed manual `vehicle_type_id` / `member_group_id` text inputs

#### Reports (`pages/report.vue`)
- Default date range pre-filled to today (`YYYY-MM-DD` format)
- Report type dropdown preserved

#### DataTable.vue
- Added `server-side` prop for server-side pagination mode
- Emits `page-change` / `page-size-change` events for parent-controlled pagination

#### Transactions (`pages/transaksi.vue`)
- Switched to **server-side pagination** using `PaginatedList` schema
- `total` count from API response drives pagination

### Results
- Frontend builds cleanly: `npm run build` succeeds (~5.56 MB)
- No TypeScript errors

---

## Task 3: Redis Caching Layer

### What Changed

#### `shared/redis.py`
- Added `cache_get_json(key)` — deserialize JSON from cache
- Added `cache_set_json(key, value, ttl=300)` — serialize and store with TTL
- Added `cache_delete_pattern(pattern)` — bulk delete by glob pattern

#### `api/app/cache/reference_data.py`
- `ReferenceDataCache` class with typed methods:
  - `get_vehicle_types()` / `set_vehicle_types(data)`
  - `get_shifts()` / `set_shifts(data)`
  - `get_areas()` / `set_areas(data)`
  - `get_emoney_readers()` / `set_emoney_readers(data)`
  - `get_tariff_rules()` / `set_tariff_rules(data)`
  - `invalidate_all()` — clear all reference data caches
- TTL: 300 seconds (5 minutes)
- Key prefix: `ref:`

#### `api/app/routes/vehicle_types.py`
- `GET /vehicle_types` now checks cache first, falls back to DB on cache miss
- `POST`, `PUT`, `DELETE` invalidate the cache on success
- All cache operations wrapped in `try/except` for graceful degradation when Redis is unavailable

### Results
- Cache hit reduces DB round-trips for reference data
- Graceful fallback ensures endpoints work even without Redis

---

## Task 4: Integration Tests (Redis Streams)

### What Changed
- New file: `api/tests/test_integration_redis_streams.py`
- Uses **real Redis** (Docker) for end-to-end testing
- `IntegrationDaemon` subclass: real Redis Streams + Pub/Sub, no hardware

### Tests
1. `test_open_gate_command_flow` — API publishes open_gate → daemon receives & ACKs
2. `test_display_text_command_flow` — display_text command fields preserved
3. `test_multiple_commands_sequential` — FIFO ordering verified
4. `test_command_with_nested_dict_serialization` — JSON serialization round-trip
5. `test_daemon_event_publish` — Pub/Sub event delivery verified
6. `test_consumer_group_recreated_on_daemon_restart` — idempotent group creation
7. `test_unacked_command_redelivered` — pending message tracking

### Key Learnings
- `redis_client` singleton must be reset (`_redis = None; _instance = None`) between pytest-asyncio tests to avoid "Event loop is closed" errors
- Stream cleanup must happen **before** daemon starts so consumer groups are recreated fresh
- aioredis pub/sub `get_message()` requires polling loops in tests

### Results
- **7 integration tests** added, all pass

---

## Task 5: Deployment Configuration

### Files Created

#### `docker/docker-compose.prod.yml`
- Services: `api`, `worker-critical`, `worker-bg`, `postgres`, `redis`
- `restart: unless-stopped` for all services
- Worker profiles for selective startup
- `extra_hosts` for LAN controller access

#### `docker/nginx.conf`
- API proxy to `parking-api:8000`
- WebSocket upgrade with `proxy_read_timeout 3600s`
- Static files served directly
- SPA fallback for Nuxt routes

#### `systemd/*.service`
- `parking-api.service` — Uvicorn with 4 workers
- `parking-worker-critical.service` — ARQ critical worker
- `parking-worker-bg.service` — ARQ background worker
- `parking-daemon-gate-in@.service` — Template for gate-in daemons
- `parking-daemon-gate-out@.service` — Template for gate-out daemons

#### `scripts/deploy.sh`
- Frontend build & asset copy
- Alembic migration
- Systemd service restart
- Gate daemon instance restart

### Results
- Production deployment configuration is complete and documented
- `deploy.sh` is executable and ready for CI/CD integration

---

## Overall Metrics

| Metric | Value |
|--------|-------|
| Total tests passing | **282** |
| New tests added | **86** (79 route + 7 integration) |
| Backend coverage | All Week 6 CRUD routes |
| Frontend build | Passes (~5.56 MB) |
| Redis caching | Vehicle types (expandable to all reference data) |
| Deployment configs | Docker Compose, nginx, 5 systemd services, deploy script |

---

## Next Steps (Beyond Week 7)

1. **Hardware Integration Testing**: Deploy daemons to actual Compass/PASSTI controllers
2. **Load Testing**: k6 or Locust for API throughput validation
3. **Monitoring**: Add Prometheus metrics + Grafana dashboards
4. **Log Aggregation**: Structured JSON logs → Loki/ELK
5. **CI/CD Pipeline**: GitHub Actions or GitLab CI for automated testing + deployment
