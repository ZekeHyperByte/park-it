# Transaction Lifecycle Service

> 32 nodes · cohesion 0.10

## Key Concepts

- **create_entry_transaction()** (21 connections) — `api/app/services/transaction.py`
- **find_active_transaction()** (13 connections) — `api/app/services/transaction.py`
- **test_transaction_service.py** (9 connections) — `api/tests/test_transaction_service.py`
- **calculate_transaction_fee()** (9 connections) — `api/app/services/transaction.py`
- **transaction.py** (7 connections) — `api/app/services/transaction.py`
- **complete_exit_transaction()** (7 connections) — `api/app/services/transaction.py`
- **TestFindActiveTransaction** (7 connections) — `api/tests/test_transaction_service.py`
- **TestCalculateTransactionFee** (4 connections) — `api/tests/test_transaction_service.py`
- **TestCreateEntryTransaction** (4 connections) — `api/tests/test_transaction_service.py`
- **.test_grace_period_zero_fee()** (3 connections) — `api/tests/test_transaction_service.py`
- **.test_one_hour_fee()** (3 connections) — `api/tests/test_transaction_service.py`
- **.test_unknown_vehicle_type_defaults()** (3 connections) — `api/tests/test_transaction_service.py`
- **TestCompleteExitTransaction** (3 connections) — `api/tests/test_transaction_service.py`
- **.test_complete_cash_transaction()** (3 connections) — `api/tests/test_transaction_service.py`
- **.test_complete_rfid_transaction()** (3 connections) — `api/tests/test_transaction_service.py`
- **.test_completed_not_found()** (3 connections) — `api/tests/test_transaction_service.py`
- **.test_find_by_barcode()** (3 connections) — `api/tests/test_transaction_service.py`
- **.test_find_by_card_number()** (3 connections) — `api/tests/test_transaction_service.py`
- **.test_find_by_plate_number()** (3 connections) — `api/tests/test_transaction_service.py`
- **shift_pagi()** (2 connections) — `api/tests/test_transaction_service.py`
- **.test_create_cash_transaction()** (2 connections) — `api/tests/test_transaction_service.py`
- **.test_create_emoney_transaction()** (2 connections) — `api/tests/test_transaction_service.py`
- **.test_create_rfid_transaction()** (2 connections) — `api/tests/test_transaction_service.py`
- **.test_no_criteria_returns_none()** (2 connections) — `api/tests/test_transaction_service.py`
- **.test_not_found()** (2 connections) — `api/tests/test_transaction_service.py`
- *... and 7 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/app/services/transaction.py`
- `api/tests/test_transaction_service.py`

## Audit Trail

- EXTRACTED: 65 (50%)
- INFERRED: 66 (50%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*