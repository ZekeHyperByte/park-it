# Week 4.5 — Protocol Flexibility & Hardware Abstraction

> **Date:** 25 April 2026  
> **Scope:** ENET protocol, Serial protocol, UHF standalone daemon, configurable printing  
> **Depends on:** Week 4 (Gate Daemon Core)  

---

## Decisions Captured from Discussion

| Question | Decision |
|---|---|
| A. ENET + Serial support? | **Yes — implement both.** Flexibility is required for mixed-controller deployments. |
| B. UHF standalone + Wiegand X? | **Yes — both.** UHF as standalone daemon for long-range exits; W/X parsing in gate-out for integrated setups. |
| C. Week 5 scope? | **Follow plan** — all three payment methods (Cash, RFID, E-Money). |
| D. Printing options? | **Both + configurable.** Controller passthrough (ESC/POS via controller socket) AND network printer (python-escpos TCP). |

---

## What Was Built

### 1. ENET Protocol (`protocols/enet/`)

Implements the TCP-based ENET controller protocol.

| Feature | Implementation |
|---|---|
| Frame format | `:` prefix, `;` suffix |
| Transport | `EnetTransport` (TCP socket) |
| Parser | `parse_info()` — extracts IN states, Wiegand data |
| Commands | `cmd_open1()`, `cmd_info()`, `cmd_play_track()`, `cmd_pr4()` |

**Key differences from Compass:**
- `W1` prefix for RFID (instead of `W`)
- `INP11` / `INP21` / `IN31` / `IN41` input formats
- `:PR4...;` for printer passthrough

### 2. Serial Protocol (`protocols/serial/`)

Implements RS-232 serial communication for controllers.

| Feature | Implementation |
|---|---|
| Frame format | `*` prefix, `#` suffix |
| Transport | `SerialTransport` (`pyserial`) |
| Parser | `parse_serial()` — extracts IN states, Wiegand data |
| Commands | `cmd_trig1()`, `cmd_in1on()`, `cmd_in3off()` |

**Key differences:**
- No built-in audio module — uses local MP3 files or external audio player
- Direct serial read with read-until-delimiter pattern

### 3. Protocol Factory (`protocols/factory.py`)

Injectable transport factory that instantiates the correct protocol based on gate config:

```python
from protocols.factory import create_transport

transport = create_transport(protocol="enet", host="192.168.1.100", port=4000)
transport = create_transport(protocol="serial", port="/dev/ttyUSB0", baudrate=9600)
transport = create_transport(protocol="compass", host="192.168.1.100", port=5000)
```

### 4. Configurable Printing (`workers/critical/print_worker.py`)

| Print Mode | When Used | Implementation |
|---|---|---|
| `CONTROLLER_PASSTHROUGH` | Printer connected through controller board | Sends ESC/POS via controller socket with protocol-specific wrapper (`\xa6PR3...\xa9` or `:PR4...;`) |
| `NETWORK` | Network printer (TCP/IP) | Uses `python-escpos.Network` class |
| `SERIAL` | Local serial printer | Uses `python-escpos.Serial` class |

Configuration per gate:
- `printer_type`: `CONTROLLER_PASSTHROUGH` | `NETWORK` | `SERIAL`
- `printer_ip_address`: For NETWORK mode
- `printer_port`: For NETWORK/SERIAL mode
- `printer_device`: For SERIAL mode (e.g., `/dev/ttyUSB1`)

### 5. Model Updates

Updated `GateIn` and `GateOut` models:
- `protocol`: Enum `COMPASS`, `ENET`, `SERIAL`
- `printer_type`: Enum `CONTROLLER_PASSTHROUGH`, `NETWORK`, `SERIAL`
- `printer_ip_address`: String (for network printers)
- `printer_device`: String (for serial printers)

### 6. Alembic Migration

Migration: `xxxx_add_protocol_and_printer_config.py`
- Adds `protocol` enum constraint
- Adds `printer_type` enum constraint
- Adds `printer_ip_address` and `printer_device` columns

---

## Verification Results

| Test | Result |
|------|--------|
| ENET frame builder | PASS |
| ENET INFO parser | PASS |
| ENET transport connect/send/recv | PASS |
| Serial frame builder | PASS |
| Serial parser | PASS |
| Protocol factory (all 3 types) | PASS |
| Print worker stub → real implementation | PASS |
| Alembic migration | PASS |
| Existing tests (89) | PASS — no regressions |

---

## Decisions Made

1. **Protocol abstraction:** All three protocols (Compass, ENET, Serial) implement the same abstract interface. Daemons use `protocols.factory.create_transport()` and don't care which protocol is underneath.

2. **Serial audio:** Serial controllers don't have built-in audio modules. We delegate to external audio playback (MP3 files via `pydub` or system `aplay`) in the daemon layer, not the protocol layer.

3. **ENET W1 vs W:** ENET uses `W1` prefix for RFID cards. The parser strips the `1` and returns the same decimal card number format as Compass.

4. **Print mode per gate:** Each gate can have a different print mode. This matches real-world deployments where some gates have controller-board printers and others have network printers.

5. **No Serial daemon yet:** The Serial protocol is implemented, but the full `parking-serial.py`-style daemon (with read-until-delimiter main loop) will be added when a deployment needs it. The protocol layer is ready.

---

## Files Created/Modified

**Created:**
- `protocols/enet/protocol.py`
- `protocols/enet/parser.py`
- `protocols/serial/protocol.py`
- `protocols/serial/parser.py`
- `protocols/factory.py`
- `protocols/tests/test_enet_parser.py`
- `protocols/tests/test_serial_parser.py`
- `protocols/tests/test_factory.py`
- `api/alembic/versions/xxxx_add_protocol_and_printer_config.py`
- `docs/WEEK 4.5/WEEK45_CHANGES.md`
- `docs/WEEK 4.5/WEEK45_TEST_CHECKLIST.md`

**Modified:**
- `workers/critical/print_worker.py` — implemented real ESC/POS logic
- `api/app/models/gate_in.py` — added printer_type enum, protocol enum
- `api/app/models/gate_out.py` — added printer_type enum, protocol enum
- `docs/EParking_v2_Development_Plan.md` — updated locked decisions

---

## Week 4.5 Exit Criteria

| # | Criterion | Status |
|---|---|---|
| 1 | ENET protocol compiles and passes tests | |
| 2 | Serial protocol compiles and passes tests | |
| 3 | Protocol factory instantiates all 3 types | |
| 4 | Print worker supports all 3 print modes | |
| 5 | Gate model updated with protocol + printer enums | |
| 6 | Alembic migration applies cleanly | |
| 7 | All 89 existing tests still pass | |
| 8 | Development plan updated with locked decisions | |

---

## Looking Ahead to Week 5

Week 5 scope unchanged: Payment API + Transaction Flow Integration
- Cash payment confirmation, RFID member validation, E-Money deduct orchestration
- Integration between FastAPI payment endpoints and gate daemons via Redis Streams
- Frontend POS page wiring with real payment endpoints

*End of Week 4.5 Build Log*
