# Week 9 — Changes & Build Log

> **Date:** 26 April 2026
> **Scope:** Observability, E2E Integration & CI/CD

## What Was Built

### 1. E2E Daemon Integration Tests
- `tests/e2e/conftest.py` — `GateOrchestrator` helper for spinning up real daemons against TCP simulators
- `tests/e2e/test_gate_in_orchestration.py` — Gate-in Cash and E-Money flows with event capture
- `tests/e2e/test_gate_out_orchestration.py` — Gate-out Cash, RFID, E-Money, and timeout flows
- Fixed `BaseDaemon.run()` to call `_on_started()` hook after `_running=True`, ensuring subclass polling starts correctly
- Fixed `GateInDaemon` and `GateOutDaemon` to use `_on_started()` for controller polling
- Fixed `gate_out.py` to only create `passti_transport` when `emoney_reader_id` is configured, preventing event loop starvation from blocking PASSTI polls
- Fixed `gate_in.py` to only create `passti_transport` in EMONEY mode

### 2. Prometheus Metrics
- `api/app/middleware/metrics.py` — HTTP request counter + latency histogram, payment counters, settlement counter
- `/metrics` endpoint exposed for Prometheus scraping
- Payment routes increment `payment_attempts_total` and `payment_success_total` labeled by method
- Metrics middleware tracks all HTTP requests excluding `/metrics` itself

### 3. Advanced Health Checks
- `GET /api/health?detailed=true` returns DB + Redis connectivity status
- Returns `degraded` if any dependency is down
- Basic `/api/health` still returns simple `{"status": "ok"}`

### 4. Load Testing
- `tests/load/locustfile.py` — Locust scenarios for health, transactions, settings, settlements
- `tests/load/README.md` — Instructions for running load tests

### 5. CI/CD Pipeline
- `.github/workflows/ci.yml` — GitHub Actions workflow running on push/PR
- PostgreSQL 16 + Redis 7 services
- Alembic migrations, pytest, circular import check, route count verification

## Verification Results

| Test | Result |
|------|--------|
| Full existing test suite | 302 passed (1 pre-existing flaky test in settlement worker when run in full suite) |
| E2E gate-in orchestration | PASS (2/2) |
| E2E gate-out orchestration | PASS (4/4) |
| Simulator tests | PASS (4/4) |
| Metrics endpoint | PASS (5/5) |
| Advanced health check | PASS (2/2) |
| Circular imports | PASS |
| Route count | 70 |
| Frontend build | N/A (no frontend changes) |

## Known Issues

| Issue | Description | Status |
|-------|-------------|--------|
| `test_no_unsettled_transactions` flaky | `workers/tests/test_settlement_worker.py::TestGenerateSettlementFile::test_no_unsettled_transactions` occasionally fails with `RuntimeError: Event loop is closed` when run in the full 300+ test suite. Passes when run alone or in smaller batches. Pre-existing issue, not introduced by Week 9 changes. | **Known** |

## Exit Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | E2E tests orchestrate real daemons + simulators | ✅ |
| 2 | Prometheus /metrics endpoint functional | ✅ |
| 3 | Advanced health checks DB + Redis | ✅ |
| 4 | Load test suite created | ✅ |
| 5 | CI/CD pipeline configured | ✅ |
| 6 | All tests pass (except 1 pre-existing flaky) | ✅ |
| 7 | Documentation complete | ✅ |
