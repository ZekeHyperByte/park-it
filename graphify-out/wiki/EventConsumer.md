# EventConsumer

> God node · 23 connections · `api/app/services/event_consumer.py`

## Connections by Relation

### calls
- [[test_event_consumer_subscribes_to_redis()]] `INFERRED`
- [[test_deduct_result_triggers_process_emoney_result()]] `INFERRED`
- [[test_event_consumer_emoney_print_decision_sends_open_gate()]] `INFERRED`

### contains
- [[event_consumer.py]] `EXTRACTED`

### method
- [[._handle_message()]] `EXTRACTED`
- [[._handle_rfid_card_read()]] `EXTRACTED`
- [[._handle_deduct_result()]] `EXTRACTED`
- [[._handle_emoney_print_decision()]] `EXTRACTED`
- [[._handle_ticket_button_pressed()]] `EXTRACTED`
- [[._listen()]] `EXTRACTED`
- [[.start()]] `EXTRACTED`
- [[._handle_passti_card_tap()]] `EXTRACTED`
- [[._handle_help_button_pressed()]] `EXTRACTED`
- [[._handle_vehicle_detected()]] `EXTRACTED`
- [[.stop()]] `EXTRACTED`
- [[.__init__()]] `EXTRACTED`

### rationale_for
- [[Subscribe to Redis pub/sub and process events server-side.]] `EXTRACTED`

### uses
- [[OpenGateCommand]] `INFERRED`
- [[DeductStatus]] `INFERRED`
- [[MockPubSub]] `INFERRED`
- [[DisplayTextCommand]] `INFERRED`
- [[PlayAudioCommand]] `INFERRED`
- [[PrintTicketThenOpenCommand]] `INFERRED`

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*