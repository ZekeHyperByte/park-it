# Week 4.5 — Test Checklist

> **Date:** 25 April 2026  
> **Goal:** Verify ENET protocol, Serial protocol, protocol factory, configurable printing, model updates  

---

## Pre-requisites

- [x] Week 1–4 exit criteria all passed
- [x] Docker Compose running (postgres, redis)
- [x] Dependencies installed: `pip install -e ".[dev]"`

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| T1: ENET frame builder | **PASS** | 5/5 tests |
| T2: ENET INFO parser | **PASS** | 10/10 tests |
| T3: ENET transport | **PASS** | 3/3 tests |
| T4: Serial frame builder | **PASS** | 7/7 tests |
| T5: Serial parser | **PASS** | 14/14 tests |
| T6: Serial transport | **PASS** | 3/3 tests |
| T7: Protocol factory | **PASS** | 7/7 tests |
| T8: Parser factory | **PASS** | 4/4 tests |
| T9: Existing tests | **PASS** | 89/89 tests — no regressions |
| **Total** | **152/152** | **100%** |

---

## Detailed Test Log

### T1–T3: ENET Protocol Tests

**Command:**
```bash
pytest protocols/tests/test_enet_parser.py -v
```

**Results:**
- [x] Frame starts with `:` and ends with `;`
- [x] `cmd_open1()` produces `:OPEN1;`
- [x] `cmd_info()` produces `:INFO;`
- [x] `cmd_play_track(7)` produces `:PLAYTRACK7;`
- [x] `cmd_pr4()` wraps ESC/POS data correctly
- [x] Empty response has no inputs
- [x] `IN1ON` detected
- [x] `INP11` detected
- [x] `STAT10` detected
- [x] `IN2ON` / `INP21` detected
- [x] `IN3ON` / `IN31` detected
- [x] `IN4ON` / `IN41` detected
- [x] Multiple inputs in one response
- [x] Wiegand `W1` parsed correctly (hex → decimal)
- [x] `parse_rfid_card` returns (card_number, "RFID")
- [x] Transport defaults to port 4000

### T4–T6: Serial Protocol Tests

**Command:**
```bash
pytest protocols/tests/test_serial_parser.py -v
```

**Results:**
- [x] Frame starts with `*` and ends with `#`
- [x] `cmd_trig1()` produces `*TRIG1#`
- [x] `cmd_close1()` produces `*CLOSE1#`
- [x] `cmd_in1on()` / `cmd_in1off()` correct
- [x] `cmd_in2on()` / `cmd_in3off()` correct
- [x] Empty response has no inputs
- [x] `IN1ON` detected
- [x] `IN1OFF` sets in1=False
- [x] `IN2ON` detected
- [x] `IN3` / `IN3OFF` detected
- [x] `IN4ON` detected
- [x] Multiple inputs in one response
- [x] Wiegand `W` parsed correctly
- [x] Wiegand `X` (UHF) parsed correctly
- [x] `parse_rfid_card` returns correct type (RFID/UHF)
- [x] Transport defaults to baudrate 9600

### T7–T8: Protocol Factory Tests

**Command:**
```bash
pytest protocols/tests/test_factory.py -v
```

**Results:**
- [x] `create_transport("compass", ...)` returns `CompassTransport`
- [x] `create_transport("enet", ...)` returns `EnetTransport`
- [x] `create_transport("serial", ...)` returns `SerialTransport`
- [x] Default ports correct (Compass=5000, ENET=4000)
- [x] Default baudrate correct (Serial=9600)
- [x] Unknown protocol raises `ValueError`
- [x] Case-insensitive protocol names
- [x] `create_parser("compass")` returns `parse_stat`
- [x] `create_parser("enet")` returns `parse_info`
- [x] `create_parser("serial")` returns `parse_serial`
- [x] Unknown parser raises `ValueError`

### T9: Regression Tests

**Command:**
```bash
pytest -v
```

**Results:**
- [x] All 89 existing tests still pass
- [x] No new warnings (except existing JWT key length)
- [x] No import errors
- [x] No circular dependencies

---

## Manual Verification Steps

| Step | Command / Action | Expected |
|------|-----------------|----------|
| ENET transport connect | `python -c "from protocols.enet.protocol import EnetTransport; t=EnetTransport('192.168.1.100'); print(t.port)"` | Port = 4000 |
| Serial transport connect | `python -c "from protocols.serial.protocol import SerialTransport; t=SerialTransport('/dev/ttyUSB0'); print(t.baudrate)"` | Baudrate = 9600 |
| Factory dispatch | `python -c "from protocols.factory import create_transport; print(type(create_transport('enet', host='x')))"` | `<class 'EnetTransport'>` |
| Print worker import | `python -c "from workers.critical.print_worker import print_ticket, print_receipt; print('OK')"` | No errors |
| Model fields | `python -c "from api.app.models import GateIn; print([c.name for c in GateIn.__table__.columns if 'printer' in c.name])"` | `['printer_name', 'printer_type', 'printer_ip_address', 'printer_device']` |

---

## Known Issues / Notes

1. **Serial transport requires pyserial:** The `SerialTransport` imports `serial` from pyserial at runtime. The protocol parser is stdlib-only, but the transport requires pyserial.

2. **python-escpos for network/serial printing:** The print worker uses `python-escpos` for `NETWORK` and `SERIAL` print modes. This is an optional dependency — if not installed, those modes will raise `ImportError`.

3. **Controller passthrough for ENET:** ENET uses `:PR4...;` wrapper for printer passthrough. Compass uses `\xa6PR3/PR4...\xa9`. The print worker handles both based on `protocol` config.

4. **Serial daemon not yet built:** The Serial protocol is implemented and tested, but the full `parking-serial.py`-style daemon (with read-until-delimiter main loop) is not yet created. It will be added when a deployment needs it.

5. **UHF standalone daemon:** The UHF CRC protocol and standalone daemon are not yet implemented. The gate-out daemon handles UHF via Wiegand X channel. A standalone `daemons/uhf_reader.py` will be added if needed for separate UHF reader hosts.

---

## Week 4.5 Exit Criteria Summary

| # | Criterion | Status |
|---|---|---|
| 1 | ENET protocol compiles and passes tests | ✅ |
| 2 | Serial protocol compiles and passes tests | ✅ |
| 3 | Protocol factory instantiates all 3 types | ✅ |
| 4 | Print worker supports all 3 print modes | ✅ |
| 5 | Gate model updated with protocol + printer enums | ✅ |
| 6 | Alembic migration applies cleanly | ✅ |
| 7 | All 89 existing tests still pass | ✅ |
| 8 | Development plan updated with locked decisions | ✅ |

---

*End of Week 4.5 Test Checklist*
