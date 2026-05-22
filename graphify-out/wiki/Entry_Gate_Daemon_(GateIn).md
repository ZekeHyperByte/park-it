# Entry Gate Daemon (GateIn)

> 40 nodes · cohesion 0.11

## Key Concepts

- **GateInDaemon** (62 connections) — `daemons/gate_in.py`
- **._send_controller_command()** (16 connections) — `daemons/gate_in.py`
- **cmd_ds()** (11 connections) — `protocols/compass/protocol.py`
- **.handle_command()** (11 connections) — `daemons/gate_in.py`
- **._cmd_play_audio()** (10 connections) — `daemons/gate_in.py`
- **._cmd_print_ticket_then_open()** (10 connections) — `daemons/gate_in.py`
- **._on_help_button()** (8 connections) — `daemons/gate_in.py`
- **._on_vehicle_detected()** (8 connections) — `daemons/gate_in.py`
- **._cmd_check_balance()** (7 connections) — `daemons/gate_in.py`
- **._on_vehicle_passed()** (7 connections) — `daemons/gate_in.py`
- **PlayAudioEvent** (7 connections) — `shared/events.py`
- **VehiclePassedEvent** (7 connections) — `shared/events.py`
- **._cmd_open_gate()** (6 connections) — `daemons/gate_in.py`
- **GateOpenedEvent** (6 connections) — `shared/events.py`
- **._connect_controller()** (5 connections) — `daemons/gate_in.py`
- **HelpButtonPressedEvent** (5 connections) — `shared/events.py`
- **._check_passti_tap()** (4 connections) — `daemons/gate_in.py`
- **._cmd_display_text()** (4 connections) — `daemons/gate_in.py`
- **._cmd_reset_gate()** (4 connections) — `daemons/gate_in.py`
- **._on_gate_opened()** (4 connections) — `daemons/gate_in.py`
- **._relay_brake()** (4 connections) — `daemons/gate_in.py`
- **._relay_close()** (4 connections) — `daemons/gate_in.py`
- **._cmd_print_ticket()** (3 connections) — `daemons/gate_in.py`
- **._passti_poll_loop()** (3 connections) — `daemons/gate_in.py`
- **._relay_open()** (3 connections) — `daemons/gate_in.py`
- *... and 15 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `daemons/gate_in.py`
- `protocols/compass/protocol.py`
- `shared/events.py`

## Audit Trail

- EXTRACTED: 172 (72%)
- INFERRED: 68 (28%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*