# Daemon Runner & Controller Connection

> 26 nodes · cohesion 0.09

## Key Concepts

- **ControllerPassthroughTransport** (10 connections) — `protocols/passti/transport.py`
- **DirectSerialTransport** (8 connections) — `protocols/passti/transport.py`
- **._connect_controller()** (7 connections) — `daemons/gate_out.py`
- **transport.py** (7 connections) — `protocols/passti/transport.py`
- **EmoneyReaderTransport** (5 connections) — `protocols/passti/transport.py`
- **ABC** (4 connections)
- **.run()** (3 connections) — `daemons/gate_out.py`
- **.send_recv()** (3 connections) — `protocols/passti/transport.py`
- **.send_recv()** (3 connections) — `protocols/passti/transport.py`
- **.close()** (2 connections) — `protocols/passti/transport.py`
- **.__init__()** (2 connections) — `protocols/passti/transport.py`
- **.__init__()** (2 connections) — `protocols/passti/transport.py`
- **Connect to gate controller (TCP or serial based on protocol config).** (1 connections) — `daemons/gate_out.py`
- **Start daemon: connect controller, then delegate to base run.** (1 connections) — `daemons/gate_out.py`
- **close()** (1 connections) — `protocols/passti/transport.py`
- **.close()** (1 connections) — `protocols/passti/transport.py`
- **PASSTI reader transport abstraction.  Supports two connection modes: 1. Controll** (1 connections) — `protocols/passti/transport.py`
- **No-op — socket is managed by the gate controller.** (1 connections) — `protocols/passti/transport.py`
- **Reader connected directly to PC via USB-to-Serial or RS-232.      Uses pyserial** (1 connections) — `protocols/passti/transport.py`
- **Initialize with serial port settings.          Args:             port: Serial po** (1 connections) — `protocols/passti/transport.py`
- **Abstract transport for PASSTI e-money reader.** (1 connections) — `protocols/passti/transport.py`
- **Send frame via direct serial and read response.** (1 connections) — `protocols/passti/transport.py`
- **Reader connected to controller Serial2.      Sends commands via controller's QR5** (1 connections) — `protocols/passti/transport.py`
- **Initialize with a shared TCP socket to the controller.          Args:** (1 connections) — `protocols/passti/transport.py`
- **Send frame via controller passthrough and read response.          Uses PASSTI fr** (1 connections) — `protocols/passti/transport.py`
- *... and 1 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `daemons/gate_out.py`
- `protocols/passti/transport.py`

## Audit Trail

- EXTRACTED: 58 (83%)
- INFERRED: 12 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*