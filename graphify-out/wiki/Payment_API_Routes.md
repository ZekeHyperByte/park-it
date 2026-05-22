# Payment API Routes

> 23 nodes · cohesion 0.14

## Key Concepts

- **payments.py** (9 connections) — `api/app/routes/payments.py`
- **PaymentResponse** (9 connections) — `api/app/schemas/payment.py`
- **cash_payment()** (8 connections) — `api/app/routes/payments.py`
- **rfid_payment()** (8 connections) — `api/app/routes/payments.py`
- **emoney_result()** (7 connections) — `api/app/routes/payments.py`
- **emoney_booth_result()** (6 connections) — `api/app/routes/payments.py`
- **emoney_deduct()** (6 connections) — `api/app/routes/payments.py`
- **_get_operator_id()** (6 connections) — `api/app/routes/payments.py`
- **_check_idempotency()** (5 connections) — `api/app/routes/payments.py`
- **lookup_transaction()** (5 connections) — `api/app/routes/payments.py`
- **_store_idempotency()** (4 connections) — `api/app/routes/payments.py`
- **TransactionLookupResponse** (4 connections) — `api/app/schemas/payment.py`
- **Process RFID member payment and open gate.** (1 connections) — `api/app/routes/payments.py`
- **Initiate e-money deduct. Daemon will publish result via Pub/Sub.** (1 connections) — `api/app/routes/payments.py`
- **Process e-money deduct result (called by event handler or manually).** (1 connections) — `api/app/routes/payments.py`
- **Process e-money deduct result from booth bridge (machine-to-machine).** (1 connections) — `api/app/routes/payments.py`
- **Look up an active transaction by barcode, card, or plate.** (1 connections) — `api/app/routes/payments.py`
- **Check if a payment with this idempotency key was already processed.** (1 connections) — `api/app/routes/payments.py`
- **Cache a payment response for idempotency deduplication.** (1 connections) — `api/app/routes/payments.py`
- **Extract operator ID from JWT payload.** (1 connections) — `api/app/routes/payments.py`
- **Process cash payment and open gate.** (1 connections) — `api/app/routes/payments.py`
- **Standard payment response.** (1 connections) — `api/app/schemas/payment.py`
- **Active transaction lookup response.** (1 connections) — `api/app/schemas/payment.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/app/routes/payments.py`
- `api/app/schemas/payment.py`

## Audit Trail

- EXTRACTED: 60 (68%)
- INFERRED: 28 (32%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*