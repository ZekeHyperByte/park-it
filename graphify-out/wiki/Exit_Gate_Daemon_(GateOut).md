# Exit Gate Daemon (GateOut)

> 50 nodes · cohesion 0.07

## Key Concepts

- **GateOutDaemon** (68 connections) — `daemons/gate_out.py`
- **._send_controller_command()** (13 connections) — `daemons/gate_out.py`
- **.handle_command()** (12 connections) — `daemons/gate_out.py`
- **._cmd_play_audio()** (9 connections) — `daemons/gate_out.py`
- **._initialize_gate_position()** (7 connections) — `daemons/gate_out.py`
- **._on_payment_timeout()** (7 connections) — `daemons/gate_out.py`
- **._on_vehicle_passed()** (7 connections) — `daemons/gate_out.py`
- **._cmd_deduct()** (6 connections) — `daemons/gate_out.py`
- **._cmd_display_text()** (5 connections) — `daemons/gate_out.py`
- **._cmd_open_gate()** (5 connections) — `daemons/gate_out.py`
- **._relay_brake()** (5 connections) — `daemons/gate_out.py`
- **._relay_close()** (5 connections) — `daemons/gate_out.py`
- **._relay_open()** (5 connections) — `daemons/gate_out.py`
- **._start_polling()** (5 connections) — `daemons/gate_out.py`
- **DeductResultEvent** (5 connections) — `shared/events.py`
- **TimeoutAlertEvent** (5 connections) — `shared/events.py`
- **._cmd_brake_gate()** (4 connections) — `daemons/gate_out.py`
- **._cmd_close_gate()** (4 connections) — `daemons/gate_out.py`
- **._cmd_print_receipt()** (4 connections) — `daemons/gate_out.py`
- **._cmd_reset_gate()** (4 connections) — `daemons/gate_out.py`
- **._on_gate_opened()** (4 connections) — `daemons/gate_out.py`
- **._on_started()** (4 connections) — `daemons/gate_out.py`
- **._rfid_serial_reader_task()** (4 connections) — `daemons/gate_out.py`
- **._vehicle_pass_timer()** (4 connections) — `daemons/gate_out.py`
- **._cmd_buzzer()** (3 connections) — `daemons/gate_out.py`
- *... and 25 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `daemons/gate_out.py`
- `shared/events.py`

## Audit Trail

- EXTRACTED: 186 (81%)
- INFERRED: 45 (19%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*