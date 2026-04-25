# Week 5 — Payment API + Transaction Flow Integration

> **Date:** 25 April 2026
> **Scope:** Payment orchestration endpoints, transaction services, Redis command integration, frontend POS wiring
> **Depends on:** Week 1–4.5 (Foundation, Auth, Frontend, Daemons, Protocols)

---

## Architecture

FastAPI payment routes receive HTTP requests from the POS frontend, use SQLAlchemy async sessions to read/write transactions, and publish Redis Stream commands to gate daemons. The daemon state machines (built in Week 4) handle hardware; FastAPI handles business logic.

**Tech Stack:** FastAPI, SQLAlchemy async, Redis Streams, Pydantic, Nuxt 3/Pinia

---

## Task 1: Transaction Service

**Files:**
- Create: `api/app/services/transaction.py`
- Test: `api/tests/test_transaction_service.py`

**Steps:**
1. Write failing tests for transaction CRUD operations
2. Implement `create_entry_transaction()`, `find_active_transaction()`, `complete_exit_transaction()`, `get_current_shift()`
3. Run tests — expect PASS
4. Commit

---

## Task 2: Payment Service

**Files:**
- Create: `api/app/services/payment.py`
- Test: `api/tests/test_payment_service.py`

**Steps:**
1. Write failing tests for cash, RFID, e-money payment flows
2. Implement `process_cash_payment()`, `process_rfid_payment()`, `process_emoney_deduct()`, `process_emoney_result()`
3. Run tests — expect PASS
4. Commit

---

## Task 3: Redis Command Publisher

**Files:**
- Create: `api/app/services/gate_command.py`
- Test: `api/tests/test_gate_command.py`

**Steps:**
1. Write failing test for publishing commands to Redis Streams
2. Implement `publish_command()` helper that serializes Pydantic commands and calls `redis_client.xadd()`
3. Run tests — expect PASS
4. Commit

---

## Task 4: Payment Schemas

**Files:**
- Create: `api/app/schemas/payment.py`

**Steps:**
1. Create Pydantic schemas: `CashPaymentRequest`, `RfidPaymentRequest`, `EmoneyDeductRequest`, `PaymentResponse`, `TransactionLookupResponse`
2. Verify imports compile
3. Commit

---

## Task 5: Payment Routes

**Files:**
- Create: `api/app/routes/payments.py`
- Modify: `api/app/main.py` to include router
- Test: `api/tests/test_payment_routes.py`

**Steps:**
1. Write failing integration tests for each endpoint
2. Implement routes with proper auth, DB access, Redis publishing
3. Mount router in `main.py`
4. Run tests — expect PASS
5. Commit

---

## Task 6: Frontend POS Wiring

**Files:**
- Modify: `frontend/pages/index.vue`
- Modify: `frontend/stores/gate.js`

**Steps:**
1. Update POS page to call real payment endpoints
2. Add barcode/ plate lookup on vehicle detection
3. Wire RFID payment flow
4. Wire E-Money payment flow (deduct request + result handling)
5. Add keyboard shortcuts (F1 Cash, F2 RFID, F3 E-Money)
6. Build and verify compilation
7. Commit

---

## Task 7: Regression Tests

**Command:** `pytest -v`
**Expected:** All existing tests (152) + new tests pass

---

## Exit Criteria

| # | Criterion |
|---|---|
| 1 | `POST /api/payments/cash` processes cash payment and publishes `open_gate` |
| 2 | `POST /api/payments/rfid` validates member and publishes `open_gate` |
| 3 | `POST /api/payments/emoney/deduct` sends deduct command to daemon |
| 4 | `POST /api/payments/emoney/result` handles deduct result and updates transaction |
| 5 | `GET /api/transactions/active` finds active transaction by barcode/card/plate |
| 6 | Frontend POS calls real endpoints and handles responses |
| 7 | All 152+ existing tests pass |
| 8 | New tests cover all payment flows |
| 9 | No circular imports |
| 10 | Documentation written |
