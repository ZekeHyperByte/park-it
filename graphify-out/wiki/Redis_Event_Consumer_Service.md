# Redis Event Consumer Service

> 32 nodes · cohesion 0.09

## Key Concepts

- **EventConsumer** (23 connections) — `api/app/services/event_consumer.py`
- **publish_command()** (19 connections) — `api/app/services/gate_command.py`
- **._handle_message()** (10 connections) — `api/app/services/event_consumer.py`
- **._handle_rfid_card_read()** (10 connections) — `api/app/services/event_consumer.py`
- **._handle_deduct_result()** (8 connections) — `api/app/services/event_consumer.py`
- **PlayAudioCommand** (8 connections) — `shared/events.py`
- **._handle_emoney_print_decision()** (7 connections) — `api/app/services/event_consumer.py`
- **._handle_ticket_button_pressed()** (7 connections) — `api/app/services/event_consumer.py`
- **._listen()** (5 connections) — `api/app/services/event_consumer.py`
- **._handle_help_button_pressed()** (3 connections) — `api/app/services/event_consumer.py`
- **._handle_passti_card_tap()** (3 connections) — `api/app/services/event_consumer.py`
- **._handle_vehicle_detected()** (3 connections) — `api/app/services/event_consumer.py`
- **.start()** (3 connections) — `api/app/services/event_consumer.py`
- **event_consumer.py** (2 connections) — `api/app/services/event_consumer.py`
- **gate_command.py** (2 connections) — `api/app/services/gate_command.py`
- **.stop()** (2 connections) — `api/app/services/event_consumer.py`
- **.__init__()** (1 connections) — `api/app/services/event_consumer.py`
- **Redis Pub/Sub event consumer for server-side event processing.  Subscribes to pa** (1 connections) — `api/app/services/event_consumer.py`
- **Handle print decision at entry gate — create transaction and open gate.** (1 connections) — `api/app/services/event_consumer.py`
- **Handle deduct_result event by processing the e-money payment.** (1 connections) — `api/app/services/event_consumer.py`
- **Subscribe to Redis pub/sub and process events server-side.** (1 connections) — `api/app/services/event_consumer.py`
- **Cash entry: create transaction, send print_ticket_then_open to daemon.** (1 connections) — `api/app/services/event_consumer.py`
- **Start the Redis pub/sub listener.** (1 connections) — `api/app/services/event_consumer.py`
- **RFID/UHF card read — branches on gate direction: entry creates tx, exit closes t** (1 connections) — `api/app/services/event_consumer.py`
- **Stop the Redis pub/sub listener.** (1 connections) — `api/app/services/event_consumer.py`
- *... and 7 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/app/services/event_consumer.py`
- `api/app/services/gate_command.py`
- `shared/events.py`

## Audit Trail

- EXTRACTED: 78 (60%)
- INFERRED: 53 (40%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*