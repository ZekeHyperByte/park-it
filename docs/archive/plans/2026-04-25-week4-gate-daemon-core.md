# Week 4 — Gate Daemon Core Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the gate daemon core — `daemons/base.py`, `daemons/gate_in.py`, `daemons/gate_out.py` — with Redis Streams consumer groups, heartbeat, state persistence, full state machines, and comprehensive test coverage.

**Architecture:** Three-layer daemon architecture: (1) `BaseDaemon` handles Redis Streams ACK-based command consumption, Pub/Sub event publishing, heartbeat, and state persistence; (2) `GateInDaemon` extends BaseDaemon with the full gate-in state machine for Cash/RFID/E-Money modes; (3) `GateOutDaemon` extends BaseDaemon with the full gate-out state machine including three concurrent asyncio tasks for payment method resolution. All daemons use `protocols/compass/` for TCP controller communication and `protocols/passti/` for e-money reader passthrough.

**Tech Stack:** Python 3.12+, asyncio, redis-py (async), pydantic (events), structlog, pytest-asyncio

---

## Task 1: Create `daemons/__init__.py`

**Files:**
- Create: `daemons/__init__.py`

**Step 1: Create module init**

```python
"""Gate daemon package."""
```

**Step 2: Verify import**

Run: `python -c "import daemons; print('daemons OK')"`
Expected: `daemons OK`

---

## Task 2: Create `daemons/base.py` — Abstract Base Daemon

**Files:**
- Create: `daemons/base.py`
- Test: `daemons/tests/test_base.py`

**Step 1: Write the failing test**

Test `BaseDaemon` instantiation, state persistence round-trip, event publishing, and heartbeat scheduling.

**Step 2: Run test to verify it fails**

Run: `pytest daemons/tests/test_base.py -v`
Expected: ModuleNotFoundError or import errors

**Step 3: Implement `daemons/base.py`**

Key components:
- `BaseDaemon` abstract class with `__init__(gate_id, config)`
- Redis connection via `shared/redis.py` `redis_client`
- `run()` main loop: consume commands from Redis Streams (`parking.commands.{gate_id}`)
- Consumer group creation (`xgroup_create` with `mkstream=True`)
- `xreadgroup` with 5s block timeout
- Auto-ACK after successful processing, or NACK/retry on failure
- `publish_event()` method for Pub/Sub events to `parking.events.{gate_id}`
- Heartbeat coroutine: every 30s publish `HeartbeatEvent`
- State persistence: `hset` to `daemon:state:{gate_id}` on every state transition
- State recovery: `hgetall` from `daemon:state:{gate_id}` on startup
- Graceful shutdown: cancel tasks, close Redis
- `_transition(state)` helper that persists and logs
- Abstract methods: `handle_command()`, `get_initial_state()`

**Step 4: Run tests**

Run: `pytest daemons/tests/test_base.py -v`
Expected: All tests pass

---

## Task 3: Create `daemons/gate_in.py` — Gate-In State Machine

**Files:**
- Create: `daemons/gate_in.py`
- Test: `daemons/tests/test_gate_in.py`

**Step 1: Write failing tests for Cash mode flow**

Test IDLE → VEHICLE_PRESENT → GATE_CLOSED → WAITING_BUTTON → PROCESSING → OPENING → IDLE

**Step 2: Run tests — expect fail**

**Step 3: Implement GateInDaemon**

States: `IDLE`, `VEHICLE_PRESENT`, `GATE_CLOSED`, `WAITING_BUTTON`, `WAITING_CARD`, `VALIDATING`, `CHECKING_BALANCE`, `WAITING_PRINT_DECISION`, `PROCESSING`, `OPENING`

Methods:
- Cash: `handle_ticket_button()`, `handle_process_ticket()`
- RFID: `handle_rfid_card()`, `handle_validate_member()`
- E-Money: `handle_passti_tap()`, `handle_check_balance()`, `handle_print_decision()`

Controller integration:
- `CompassTransport` for TCP commands
- `send_close_gate()` on VEHICLE_PRESENT
- `send_open_gate()` on successful processing
- `send_play_audio(track)` for feedback
- `send_display_text(line1, line2)` for driver feedback

E-Money integration:
- `ControllerPassthroughTransport` for PASSTI via controller Serial2
- `cmd_check_balance()` → parse response → threshold check
- `cmd_deduct()` (stub for gate-in, actual deduct in gate-out)
- Print decision: 10s timer, IN2 button or timeout

Snapshot trigger:
- ARQ enqueue `take_snapshot` on GATE_CLOSED (stub via Redis event for now)

**Step 4: Run tests**

Run: `pytest daemons/tests/test_gate_in.py -v`
Expected: All tests pass

---

## Task 4: Create `daemons/gate_out.py` — Gate-Out State Machine

**Files:**
- Create: `daemons/gate_out.py`
- Test: `daemons/tests/test_gate_out.py`

**Step 1: Write failing tests**

Test:
- Cash flow: POS confirms → open gate
- RFID flow: Wiegand read → validate → open gate
- E-Money flow: PASSTI tap → deduct → open gate
- Timeout flow: 120s → TIMEOUT_ALERT → operator actions
- Concurrent task cancellation: when one wins, others are cancelled

**Step 2: Run tests — expect fail**

**Step 3: Implement GateOutDaemon**

States: `IDLE`, `VEHICLE_PRESENT`, `WAITING_PAYMENT`, `TIMEOUT_ALERT`, `OPENING`

Concurrent task pattern:
```python
done, pending = await asyncio.wait(
    [task_wiegand, task_passti, task_pos, task_timeout],
    return_when=asyncio.FIRST_COMPLETED,
)
for task in pending:
    task.cancel()
```

Task implementations:
- `task_wiegand`: poll controller STAT for W/X data, parse with `parse_rfid_card()`
- `task_passti`: poll for PASSTI card tap (via controller or direct reader)
- `task_pos`: wait for `cash_payment_confirmed` Redis Stream command
- `task_timeout`: `asyncio.sleep(payment_timeout_seconds)`

Timeout handling:
- Publish `timeout_alert` event
- Display "Mohon Hubungi Petugas", play audio track 8
- Wait for: IN1 OFF (vehicle left) → log abandoned, OR operator command → resolve

E-Money exit deduct:
- Call `cmd_deduct(amount, timeout)`
- Handle all `DeductStatus` results
- Lost contact: publish intermediate event, enter correction wait
- Wrong card: display error, wait for same card
- Insufficient balance: display balance, offer alternatives

**Step 4: Run tests**

Run: `pytest daemons/tests/test_gate_out.py -v`
Expected: All tests pass

---

## Task 5: Create `daemons/tests/__init__.py` and mock fixtures

**Files:**
- Create: `daemons/tests/__init__.py`
- Create: `daemons/tests/conftest.py`

Mock fixtures needed:
- `mock_redis` — fake Redis client with xadd, xreadgroup, xack, publish, hset, hgetall
- `mock_compass_transport` — fake CompassTransport with injectable STAT responses
- `mock_passti_transport` — fake ControllerPassthroughTransport with injectable responses
- `gate_in_config` — sample GateIn config dict
- `gate_out_config` — sample GateOut config dict

---

## Task 6: Update `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

Add `daemons/tests` to testpaths:
```toml
testpaths = ["api/tests", "workers/tests", "protocols/tests", "daemons/tests"]
```

Verify `packages` includes daemons:
```toml
packages = ["api", "shared", "workers", "daemons", "protocols"]
```
(Already present — verify only)

---

## Task 7: Run full test suite

**Command:**
```bash
pytest daemons/tests -v --tb=short
pytest api/tests protocols/tests -v --tb=short
```

**Expected:** All tests pass (47 existing + new daemon tests)

---

## Task 8: Write `docs/WEEK 4/WEEK4_CHANGES.md`

Document all files created, what was built, decisions made, verification results.

---

## Task 9: Write `docs/WEEK 4/WEEK4_TEST_CHECKLIST.md`

Document all tests, commands, expected results, manual verification steps.

---

## Exit Criteria

| # | Criterion |
|---|---|
| 1 | `daemons/base.py` compiles and imports |
| 2 | `daemons/gate_in.py` compiles and imports |
| 3 | `daemons/gate_out.py` compiles and imports |
| 4 | All daemon unit tests pass |
| 5 | No circular imports (daemons → shared/events.py + protocols/ only) |
| 6 | Redis Streams consumer group logic tested |
| 7 | Heartbeat publishing tested |
| 8 | State persistence round-trip tested |
| 9 | Gate-in Cash flow tested end-to-end |
| 10 | Gate-in RFID flow tested end-to-end |
| 11 | Gate-in E-Money flow tested end-to-end |
| 12 | Gate-out concurrent task resolution tested |
| 13 | Gate-out timeout alert flow tested |
| 14 | Existing Week 1–3 tests still pass |
| 15 | Documentation written and accurate |
