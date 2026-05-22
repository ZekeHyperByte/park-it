# GateInDaemon

> God node · 62 connections · `daemons/gate_in.py`

## Connections by Relation

### contains
- [[gate_in.py]] `EXTRACTED`

### inherits
- [[BaseDaemon]] `EXTRACTED`

### method
- [[._dispatch_rss_message()]] `EXTRACTED`
- [[._send_controller_command()]] `EXTRACTED`
- [[.handle_command()]] `EXTRACTED`
- [[._cmd_play_audio()]] `EXTRACTED`
- [[._cmd_print_ticket_then_open()]] `EXTRACTED`
- [[._on_vehicle_detected()]] `EXTRACTED`
- [[._on_help_button()]] `EXTRACTED`
- [[._on_vehicle_passed()]] `EXTRACTED`
- [[._cmd_check_balance()]] `EXTRACTED`
- [[._cmd_open_gate()]] `EXTRACTED`
- [[._connect_controller()]] `EXTRACTED`
- [[._rss_listener()]] `EXTRACTED`
- [[._on_vehicle_backed_up()]] `EXTRACTED`
- [[._on_reset()]] `EXTRACTED`
- [[._on_rfid_card_read()]] `EXTRACTED`
- [[._on_passti_card_tap()]] `EXTRACTED`
- [[._rfid_serial_reader_task()]] `EXTRACTED`
- [[._relay_close()]] `EXTRACTED`
- [[._relay_brake()]] `EXTRACTED`
- [[._start_polling()]] `EXTRACTED`

### rationale_for
- [[Gate-in daemon for vehicle entry processing.]] `EXTRACTED`

### uses
- [[BaseDaemon]] `INFERRED`
- [[BaseEvent]] `INFERRED`
- [[CompassTransport]] `INFERRED`
- [[VehicleDetectedEvent]] `INFERRED`
- [[SerialTransport]] `INFERRED`
- [[ControllerPassthroughTransport]] `INFERRED`
- [[TestableGateInDaemon]] `INFERRED`
- [[PlayAudioEvent]] `INFERRED`
- [[RfidCardReadEvent]] `INFERRED`
- [[VehiclePassedEvent]] `INFERRED`
- [[GateOpenedEvent]] `INFERRED`
- [[EmoneyPrintDecisionEvent]] `INFERRED`
- [[HelpButtonPressedEvent]] `INFERRED`
- [[PasstiCardTapEvent]] `INFERRED`
- [[TicketButtonPressedEvent]] `INFERRED`
- [[TestGateInCashMode]] `INFERRED`
- [[TestGateInRfidMode]] `INFERRED`
- [[TestGateInEmoneyMode]] `INFERRED`
- [[TestGateInCommands]] `INFERRED`
- [[TestGateInAudio]] `INFERRED`

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*