# Payment Service Engine

> 38 nodes · cohesion 0.09

## Key Concepts

- **process_emoney_result()** (22 connections) — `api/app/services/payment.py`
- **test_payment_service.py** (19 connections) — `api/tests/test_payment_service.py`
- **process_cash_payment()** (14 connections) — `api/app/services/payment.py`
- **process_rfid_payment()** (14 connections) — `api/app/services/payment.py`
- **DeductStatus** (14 connections) — `shared/events.py`
- **process_emoney_deduct()** (9 connections) — `api/app/services/payment.py`
- **get_current_shift()** (7 connections) — `api/app/services/transaction.py`
- **payment.py** (6 connections) — `api/app/services/payment.py`
- **_enqueue_exit_snapshot()** (6 connections) — `api/app/services/payment.py`
- **test_success()** (5 connections) — `api/tests/test_payment_service.py`
- **test_no_active_transaction()** (3 connections) — `api/tests/test_payment_service.py`
- **test_transaction_not_found()** (3 connections) — `api/tests/test_payment_service.py`
- **TestGetCurrentShift** (3 connections) — `api/tests/test_transaction_service.py`
- **active_emoney_transaction()** (2 connections) — `api/tests/test_payment_service.py`
- **active_transaction()** (2 connections) — `api/tests/test_payment_service.py`
- **test_correction_failed()** (2 connections) — `api/tests/test_payment_service.py`
- **test_correction_verified()** (2 connections) — `api/tests/test_payment_service.py`
- **test_failed_status()** (2 connections) — `api/tests/test_payment_service.py`
- **test_insufficient_balance()** (2 connections) — `api/tests/test_payment_service.py`
- **test_invalid_member()** (2 connections) — `api/tests/test_payment_service.py`
- **test_lost_contact_intermediate()** (2 connections) — `api/tests/test_payment_service.py`
- **test_plate_lookup()** (2 connections) — `api/tests/test_payment_service.py`
- **test_timeout()** (2 connections) — `api/tests/test_payment_service.py`
- **TestProcessCashPayment** (2 connections) — `api/tests/test_payment_service.py`
- **TestProcessEmoneyDeduct** (2 connections) — `api/tests/test_payment_service.py`
- *... and 13 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/app/services/payment.py`
- `api/app/services/transaction.py`
- `api/tests/test_payment_service.py`
- `api/tests/test_transaction_service.py`
- `shared/events.py`

## Audit Trail

- EXTRACTED: 78 (47%)
- INFERRED: 88 (53%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*