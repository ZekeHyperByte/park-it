# GateOutDaemon

> God node · 68 connections · `daemons/gate_out.py`

## Connections by Relation

### contains
- [[gate_out.py]] `EXTRACTED`

### inherits
- [[BaseDaemon]] `EXTRACTED`

### method
- [[._dispatch_rss_message()]] `EXTRACTED`
- [[._send_controller_command()]] `EXTRACTED`
- [[.handle_command()]] `EXTRACTED`
- [[._start_waiting_payment()]] `EXTRACTED`
- [[._cmd_play_audio()]] `EXTRACTED`
- [[._connect_controller()]] `EXTRACTED`
- [[._initialize_gate_position()]] `EXTRACTED`
- [[._on_payment_timeout()]] `EXTRACTED`
- [[._on_vehicle_passed()]] `EXTRACTED`
- [[._rss_listener()]] `EXTRACTED`
- [[._on_vehicle_left()]] `EXTRACTED`
- [[._cmd_deduct()]] `EXTRACTED`
- [[._relay_open()]] `EXTRACTED`
- [[._relay_close()]] `EXTRACTED`
- [[._relay_brake()]] `EXTRACTED`
- [[._start_polling()]] `EXTRACTED`
- [[._on_vehicle_detected()]] `EXTRACTED`
- [[._cmd_open_gate()]] `EXTRACTED`
- [[._cmd_display_text()]] `EXTRACTED`
- [[._on_started()]] `EXTRACTED`

### rationale_for
- [[Gate-out daemon for vehicle exit processing.]] `EXTRACTED`

### uses
- [[BaseDaemon]] `INFERRED`
- [[BaseEvent]] `INFERRED`
- [[CompassTransport]] `INFERRED`
- [[VehicleDetectedEvent]] `INFERRED`
- [[DeductStatus]] `INFERRED`
- [[SerialTransport]] `INFERRED`
- [[TestableGateOutDaemon]] `INFERRED`
- [[ControllerPassthroughTransport]] `INFERRED`
- [[DirectSerialTransport]] `INFERRED`
- [[PlayAudioEvent]] `INFERRED`
- [[RfidCardReadEvent]] `INFERRED`
- [[VehiclePassedEvent]] `INFERRED`
- [[GateOpenedEvent]] `INFERRED`
- [[DeductResultEvent]] `INFERRED`
- [[PasstiCardTapEvent]] `INFERRED`
- [[TimeoutAlertEvent]] `INFERRED`
- [[VehicleLeftEvent]] `INFERRED`
- [[TestGateOutVehicleDetection]] `INFERRED`
- [[TestGateOutCashFlow]] `INFERRED`
- [[TestGateOutRfidFlow]] `INFERRED`

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*