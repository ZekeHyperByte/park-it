# Shared Event Types & Commands

> 39 nodes · cohesion 0.08

## Key Concepts

- **events.py** (39 connections) — `shared/events.py`
- **BaseCommand** (17 connections) — `shared/events.py`
- **OpenGateCommand** (15 connections) — `shared/events.py`
- **DisplayTextCommand** (9 connections) — `shared/events.py`
- **GateMode** (9 connections) — `shared/events.py`
- **test_multiple_commands_sequential()** (7 connections) — `api/tests/test_integration_redis_streams.py`
- **Enum** (6 connections)
- **PrintTicketThenOpenCommand** (5 connections) — `shared/events.py`
- **AlertType** (4 connections) — `shared/events.py`
- **DeductCommand** (4 connections) — `shared/events.py`
- **PaymentMethod** (4 connections) — `shared/events.py`
- **PrintReceiptCommand** (4 connections) — `shared/events.py`
- **ResetGateCommand** (4 connections) — `shared/events.py`
- **TransactionStatus** (4 connections) — `shared/events.py`
- **CancelCorrectionCommand** (3 connections) — `shared/events.py`
- **CancelCorrectionResultEvent** (3 connections) — `shared/events.py`
- **CashPaymentConfirmedCommand** (3 connections) — `shared/events.py`
- **CheckBalanceCommand** (3 connections) — `shared/events.py`
- **CloseGateCommand** (3 connections) — `shared/events.py`
- **EmoneyPaymentConfirmedCommand** (3 connections) — `shared/events.py`
- **ReaderErrorEvent** (3 connections) — `shared/events.py`
- **BuzzerCommand** (2 connections) — `shared/events.py`
- **GateClosedEvent** (2 connections) — `shared/events.py`
- **PrintTicketCommand** (2 connections) — `shared/events.py`
- **Pydantic schemas for all Redis IPC messages.  Daemon -> FastAPI: parking.events.** (1 connections) — `shared/events.py`
- *... and 14 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/tests/test_integration_redis_streams.py`
- `shared/events.py`

## Audit Trail

- EXTRACTED: 136 (79%)
- INFERRED: 37 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*