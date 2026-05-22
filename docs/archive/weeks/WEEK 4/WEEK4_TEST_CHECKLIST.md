# Week 4 — Test Checklist

> **Date:** 25 April 2026
> **Goal:** Verify gate daemon core — base daemon, gate-in state machine, gate-out state machine, protocol fixes

---

## Pre-requisites

- [x] Week 1–3 exit criteria all passed
- [x] Docker Compose running (postgres, redis) — for existing tests
- [x] Dependencies installed: `pip install -e ".[dev]"`
- [x] `.env` configured with JWT_SECRET

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| T1: BaseDaemon lifecycle | **PASS** | 5/5 tests |
| T2: BaseDaemon state persistence | **PASS** | 4/4 tests |
| T3: BaseDaemon event publishing | **PASS** | 1/1 tests |
| T4: BaseDaemon command consumption | **PASS** | 3/3 tests |
| T5: BaseDaemon heartbeat | **PASS** | 1/1 tests |
| T6: BaseDaemon graceful shutdown | **PASS** | 2/2 tests |
| T7: GateIn Cash mode | **PASS** | 4/4 tests |
| T8: GateIn RFID mode | **PASS** | 1/1 tests |
| T9: GateIn E-Money mode | **PASS** | 3/3 tests |
| T10: GateIn commands | **PASS** | 6/6 tests |
| T11: GateOut vehicle detection | **PASS** | 2/2 tests |
| T12: GateOut Cash flow | **PASS** | 1/1 tests |
| T13: GateOut RFID flow | **PASS** | 1/1 tests |
| T14: GateOut E-Money flow | **PASS** | 3/3 tests |
| T15: GateOut timeout alert | **PASS** | 2/2 tests |
| T16: GateOut commands | **PASS** | 3/3 tests |
| T17: Compass parser (existing) | **PASS** | 12/12 tests |
| T18: PASSTI frame (existing) | **PASS** | 8/8 tests |
| T19: API auth/tariff (existing) | **PASS** | 47/47 tests |
| **Total** | **89/89** | **100%** |

---

## Detailed Test Log

### T1–T6: BaseDaemon Tests

**Command:**
```bash
pytest daemons/tests/test_base.py -v
```

**Results:**
- [x] Daemon starts in IDLE state
- [x] run() injects fake Redis and recovers state
- [x] Consumer group created on run
- [x] Creating consumer group twice does not error (idempotent)
- [x] stop() sets running to False
- [x] State persisted to Redis Hash with state_data JSON
- [x] State recovered from Redis Hash on startup
- [x] Empty previous state defaults to initial state
- [x] _transition updates state and persists
- [x] Events published to correct Pub/Sub channel
- [x] Successful command processing results in ACK
- [x] Failed command processing does not ACK
- [x] Trace ID from command bound for logging
- [x] Heartbeat publishes to events channel
- [x] stop() cancels running tasks
- [x] Redis connection closed on shutdown

### T7–T10: GateInDaemon Tests

**Command:**
```bash
pytest daemons/tests/test_gate_in.py -v
```

**Results:**
- [x] IN1 ON transitions IDLE → VEHICLE_PRESENT
- [x] Close gate command sent on vehicle detection
- [x] After close timer, transitions to GATE_CLOSED → WAITING_BUTTON (Cash)
- [x] IN2 ON in WAITING_BUTTON transitions to PROCESSING + publishes ticket_button_pressed
- [x] open_gate command transitions to OPENING + sends TRIG1
- [x] Wiegand W read in WAITING_CARD publishes rfid_card_read event
- [x] PASSTI tap in EMONEY mode publishes passti_card_tap event
- [x] check_balance command with insufficient balance returns to IDLE + displays message
- [x] check_balance command with sufficient balance goes to WAITING_PRINT_DECISION
- [x] play_audio command sends MT to controller
- [x] display_text command sends DS to controller
- [x] reset_gate command returns to IDLE
- [x] close_gate in DUAL mode sends TRIG2
- [x] Unknown commands are ACKed (not retried)
- [x] deduct command is ignored at gate-in

### T11–T16: GateOutDaemon Tests

**Command:**
```bash
pytest daemons/tests/test_gate_out.py -v
```

**Results:**
- [x] 500ms debounce before VEHICLE_PRESENT
- [x] Vehicle detection publishes vehicle_detected event
- [x] cash_payment_confirmed resolves payment + open_gate opens gate
- [x] Wiegand card read resolves payment + publishes rfid_card_read
- [x] PASSTI tap resolves payment + publishes passti_card_tap
- [x] deduct command executes PASSTI deduct + publishes SUCCESS result
- [x] deduct with insufficient balance publishes INSUFFICIENT_BALANCE
- [x] Payment timeout transitions to TIMEOUT_ALERT + publishes event
- [x] Vehicle leaving during timeout returns to IDLE + publishes vehicle_left
- [x] open_gate from TIMEOUT_ALERT transitions to OPENING
- [x] cancel_correction command sends PASSTI cancel frame
- [x] reset_gate cancels payment tasks and returns to IDLE

### T17–T19: Existing Tests

**Command:**
```bash
pytest protocols/tests api/tests -v
```

**Results:**
- [x] Compass STAT parser: 12/12 pass
- [x] PASSTI frame builder/parser: 8/8 pass
- [x] API auth service: 6/6 pass
- [x] API JWT tokens: 6/6 pass
- [x] API password hashing: 5/5 pass
- [x] API tariff engine: 10/10 pass

---

## Full Suite Command

```bash
pytest -v
```

**Expected:** 89 tests passed, 0 failed

---

## Manual Verification Steps

The following require a running backend and Redis:

| Step | Command / Action | Expected |
|------|-----------------|----------|
| Gate-in daemon | `python -m daemons.gate_in --gate-id gate-in-1` | Daemon starts, connects to controller, begins polling |
| Gate-out daemon | `python -m daemons.gate_out --gate-id gate-out-1` | Daemon starts, connects to controller, begins polling |
| Redis consumer group | `redis-cli XINFO GROUPS parking.commands.gate-in-1` | Shows `daemon-gate-in-1` consumer group |
| Redis state | `redis-cli HGETALL daemon:state:gate-in-1` | Shows current state and state_data |
| Heartbeat events | `redis-cli SUBSCRIBE parking.events.gate-in-1` | Receives heartbeat every 30s |

---

## Known Issues / Notes

1. **MockCompassTransport repeats last response:** For testing, the mock repeats the last injected STAT response. This simulates persistent sensor state (e.g., vehicle still present) without requiring continuous injection.

2. **Test timing sensitivity:** Gate-out tests with concurrent tasks use real asyncio.sleep. Tests run in ~12–17 seconds total. Do not reduce sleeps below the minimums documented in the test files.

3. **Daemon command line interface:** The `__main__` entry point for gate_in and gate_out is not yet implemented. In production, daemons will be started via: `python -m daemons.gate_in --gate-id {id}`. This CLI wrapper will be added in Week 5.

4. **E-Money lost contact handling:** The full lost-contact state machine (LOST_CONTACT → AUTO_CORRECTION → CORRECTION_FAILED) is stubbed in the deduct command handler. Full implementation with GetLastTransaction verification will be added in Week 5/6.

5. **Camera snapshot integration:** The daemon publishes `vehicle_detected` and `gate_closed` events. The ARQ snapshot worker listens to these events (via FastAPI WebSocket/Redis bridge) and takes snapshots. Direct daemon → ARQ enqueue is not implemented to maintain the dependency contract.

---

*End of Week 4 Test Checklist*
