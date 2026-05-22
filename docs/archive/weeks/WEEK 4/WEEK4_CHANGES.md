# Week 4 — Changes & Build Log

> **Date:** 25 April 2026
> **Scope:** Gate Daemon Core
> **Depends on:** Week 1 (Foundation & Database), Week 2 (Auth, API, WebSocket, Workers), Week 3 (Frontend Foundation)

---

## What Was Built

### 1. Daemon Package (`daemons/`)

| File | Purpose |
|------|---------|
| `daemons/__init__.py` | Package init |
| `daemons/base.py` | Abstract `BaseDaemon` — Redis Streams consumer group, Pub/Sub event publishing, heartbeat (30s), state persistence/recovery, graceful shutdown |
| `daemons/gate_in.py` | `GateInDaemon` — Full gate-in state machine for CASH, RFID, EMONEY modes |
| `daemons/gate_out.py` | `GateOutDaemon` — Full gate-out state machine with asyncio.wait FIRST_COMPLETED for three concurrent payment methods |

### 2. Test Suite (`daemons/tests/`)

| File | Purpose |
|------|---------|
| `daemons/tests/__init__.py` | Test package init |
| `daemons/tests/conftest.py` | FakeRedis, MockCompassTransport, MockPasstiTransport, gate config fixtures |
| `daemons/tests/test_base.py` | 16 tests for BaseDaemon lifecycle, state persistence, event publishing, command consumption, heartbeat, graceful shutdown |
| `daemons/tests/test_gate_in.py` | 14 tests for Cash flow, RFID flow, E-Money flow, and command handlers |
| `daemons/tests/test_gate_out.py` | 12 tests for vehicle detection/debounce, Cash/RFID/E-Money concurrent resolution, timeout alert, deduct command, and reset |

### 3. Protocol Fixes

| File | Change |
|------|--------|
| `protocols/compass/parser.py` | Fixed `STAT1` vs `STAT10` ambiguity — `STAT10` no longer incorrectly triggers IN2 ON |
| `protocols/passti/commands.py` | Added `"ok": True` to `parse_deduct_response` return dict |

### 4. Configuration Update

| File | Change |
|------|--------|
| `pyproject.toml` | Added `daemons/tests` to `testpaths` |
| `shared/events.py` | Replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` |
| `daemons/base.py` | Replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` |

---

## Verification Results

| Test | Result |
|------|--------|
| BaseDaemon lifecycle | 16/16 passed |
| GateInDaemon state machine | 14/14 passed |
| GateOutDaemon state machine | 12/12 passed |
| Compass parser (existing) | 12/12 passed |
| PASSTI frame (existing) | 8/8 passed |
| API auth/tariff (existing) | 47/47 passed |
| **Total** | **89/89 passed** |

---

## Decisions Made

1. **Daemon state persistence:** Every state transition calls `_persist_state()` which writes to Redis Hash `daemon:state:{gate_id}`. On startup, `_recover_state()` restores the previous state. This enables crash recovery.

2. **FakeRedis for testing:** `daemons/tests/conftest.py` includes a `FakeRedis` class that implements xgroup_create, xreadgroup, xack, publish, hset, hgetall with in-memory storage. This allows comprehensive daemon testing without a real Redis server.

3. **Mock transport fixtures:** `MockCompassTransport` and `MockPasstiTransport` provide injectable responses for controller STAT polling and PASSTI reader communication. The compass mock repeats the last response by default to simulate persistent sensor state.

4. **Concurrent task pattern for gate-out:** `asyncio.wait(FIRST_COMPLETED)` with four tasks (wiegand, passti, pos, timeout). Winner determines payment method. Remaining tasks are cancelled.

5. **Command vs event separation:** Daemons publish hardware events (Pub/Sub) and consume commands (Redis Streams ACK-based). Business logic (transaction creation, member validation, tariff calculation) stays in FastAPI.

6. **Gate-in e-money flow:** The daemon detects PASSTI tap, publishes `passti_card_tap`, then FastAPI sends `check_balance` command. The daemon executes it and either displays insufficient balance or proceeds to print decision.

7. **Gate-out deduct flow:** FastAPI sends `deduct` command with amount. The daemon executes it on the PASSTI reader and publishes `deduct_result`. FastAPI decides next action based on status.

8. **STAT10 parser bug fixed:** `STAT10` was incorrectly matching `STAT1` and setting IN2=ON. Changed to regex `STAT1(?!0)` to require STAT1 not followed by 0.

---

## Files Created/Modified

**Created:** 8 new files across `daemons/`
- `daemons/__init__.py`
- `daemons/base.py`
- `daemons/gate_in.py`
- `daemons/gate_out.py`
- `daemons/tests/__init__.py`
- `daemons/tests/conftest.py`
- `daemons/tests/test_base.py`
- `daemons/tests/test_gate_in.py`
- `daemons/tests/test_gate_out.py`
- `docs/plans/2026-04-25-week4-gate-daemon-core.md`

**Modified:**
- `pyproject.toml` — added `daemons/tests` to testpaths
- `protocols/compass/parser.py` — fixed STAT1/STAT10 ambiguity
- `protocols/passti/commands.py` — added ok=True to parse_deduct_response
- `shared/events.py` — fixed datetime.utcnow() deprecation
- `daemons/base.py` — fixed datetime.utcnow() deprecation

**Total lines of code:** ~2,000+ (daemons + tests)

---

## Week 4 Exit Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `daemons/base.py` compiles and imports | ✅ |
| 2 | `daemons/gate_in.py` compiles and imports | ✅ |
| 3 | `daemons/gate_out.py` compiles and imports | ✅ |
| 4 | All daemon unit tests pass (42/42) | ✅ |
| 5 | No circular imports (daemons → shared/events.py + protocols/ only) | ✅ |
| 6 | Redis Streams consumer group logic tested | ✅ |
| 7 | Heartbeat publishing tested | ✅ |
| 8 | State persistence round-trip tested | ✅ |
| 9 | Gate-in Cash flow tested end-to-end | ✅ |
| 10 | Gate-in RFID flow tested end-to-end | ✅ |
| 11 | Gate-in E-Money flow tested end-to-end | ✅ |
| 12 | Gate-out concurrent task resolution tested | ✅ |
| 13 | Gate-out timeout alert flow tested | ✅ |
| 14 | Existing Week 1–3 tests still pass (47/47) | ✅ |
| 15 | Documentation written and accurate | ✅ |

---

## Looking Ahead to Week 5

**Week 5 scope:** Payment API + Transaction Flow Integration
- `api/app/routes/payments.py` — Cash payment confirmation, RFID member validation, E-Money deduct orchestration
- `api/app/services/payment.py` — Payment orchestration service
- `api/app/services/transaction.py` — Transaction creation and lookup
- Integration between FastAPI payment endpoints and gate daemons via Redis Streams
- Frontend POS page wiring with real payment endpoints

*End of Week 4 Build Log*
