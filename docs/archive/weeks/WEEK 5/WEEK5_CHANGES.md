# Week 5 — Changes & Build Log

> **Date:** 25 April 2026
> **Scope:** Payment API + Transaction Flow Integration
> **Depends on:** Week 1–4.5 (Foundation, Auth, Frontend, Daemons, Protocols)

---

## What Was Built

### 1. Transaction Service (`api/app/services/transaction.py`)

| Function | Purpose |
|----------|---------|
| `create_entry_transaction()` | Creates a new `ParkingTransaction` at vehicle entry |
| `find_active_transaction()` | Finds active (uncompleted) transaction by barcode, card, or plate |
| `calculate_transaction_fee()` | Calculates parking fee using tariff engine |
| `get_vehicle_type_tariff_config()` | Builds `TariffConfig` from DB `VehicleType` or fallback to default |
| `get_current_shift()` | Determines current shift based on time of day |
| `complete_exit_transaction()` | Marks transaction as completed with payment details |

### 2. Payment Service (`api/app/services/payment.py`)

| Function | Purpose |
|----------|---------|
| `process_cash_payment()` | Finds transaction, calculates fee, updates DB, publishes `open_gate` + `print_receipt` |
| `process_rfid_payment()` | Validates member card, finds active transaction, completes with zero fee, publishes `open_gate` + `play_audio` |
| `process_emoney_deduct()` | Finds transaction, calculates fee, publishes `deduct` command to daemon |
| `process_emoney_result()` | Handles daemon `deduct_result`, creates `EmoneyTransaction`, completes or resets transaction |

### 3. Gate Command Publisher (`api/app/services/gate_command.py`)

| Function | Purpose |
|----------|---------|
| `publish_command()` | Serializes Pydantic `RedisCommand` and publishes to `parking.commands.{gate_id}` Redis Stream |

### 4. Payment Schemas (`api/app/schemas/payment.py`)

| Schema | Purpose |
|--------|---------|
| `CashPaymentRequest` | Cash payment with gate_id, gate_out_id, barcode/plate, paid_amount |
| `RfidPaymentRequest` | RFID payment with gate_id, gate_out_id, card_number |
| `EmoneyDeductRequest` | E-money deduct initiation with gate_id, gate_out_id, card_number |
| `EmoneyResultRequest` | E-money result callback with deduct details |
| `TransactionLookupRequest` | Lookup by barcode, card, or plate |
| `PaymentResponse` | Standard payment response with success, fee, change, method |
| `TransactionLookupResponse` | Lookup response with transaction data and calculated fee |

### 5. Payment Routes (`api/app/routes/payments.py`)

| Route | Method | Access | Purpose |
|-------|--------|--------|---------|
| `/api/payments/cash` | POST | operator | Process cash payment |
| `/api/payments/rfid` | POST | operator | Process RFID member payment |
| `/api/payments/emoney/deduct` | POST | operator | Initiate e-money deduct |
| `/api/payments/emoney/result` | POST | operator | Process e-money deduct result |
| `/api/payments/lookup` | POST | operator | Find active transaction |

**Mounted in:** `api/app/main.py` at `/api/payments`

### 6. Frontend POS Wiring

| File | Changes |
|------|---------|
| `frontend/stores/gate.js` | Added `lookupTransaction()`, `confirmCashPayment()`, `processRfidPayment()`, `startEmoneyDeduct()`, `isLoading` state |
| `frontend/pages/index.vue` | Added barcode lookup input, wired all payment methods to store actions, added RFID card input modal, added keyboard shortcuts (F1/F2/F3/Escape), added duration/vehicle type display |

---

## Verification Results

| Test | Result |
|------|--------|
| Transaction service tests | 19/19 passed |
| Payment service tests | 11/11 passed |
| Payment routes tests | 8/8 passed |
| Existing tests (Weeks 1–4.5) | 152/152 passed |
| **Total tests** | **190/190 passed** |
| Frontend build | ✅ Successful (4.21 MB) |
| No circular imports | ✅ Verified |
| FastAPI app loading | ✅ All routes mounted |

---

## Decisions Made

1. **Gate-out ID nullable in tests:** Used `gate_out_id=None` in service tests to avoid FK violations against empty gate_outs table in test DB.

2. **EmoneyTransaction field name:** The model uses `amount_deducted` (not `amount`). Payment service was updated to match.

3. **Payment service returns dict:** Rather than Pydantic models, services return plain dicts for flexibility in route layer.

4. **Operator ID from JWT sub:** Routes extract `operator_id` from `sub` claim in JWT payload.

5. **Keyboard shortcuts:** F1 = Cash, F2 = RFID, F3 = E-Money, Escape = Cancel modals.

6. **Barcode lookup on POS:** Manual barcode/plate lookup field added for cash payments where card is not available.

7. **E-money SUCCESS auto-dismiss:** Frontend auto-clears transaction 3 seconds after successful e-money payment.

---

## Files Created/Modified

**Created:**
- `api/app/services/transaction.py`
- `api/app/services/payment.py`
- `api/app/services/gate_command.py`
- `api/app/schemas/payment.py`
- `api/app/routes/payments.py`
- `api/tests/test_transaction_service.py`
- `api/tests/test_payment_service.py`
- `api/tests/test_payment_routes.py`
- `docs/plans/2026-04-25-week5-payment-integration.md`
- `docs/WEEK 5/WEEK5_CHANGES.md`
- `docs/WEEK 5/WEEK5_TEST_CHECKLIST.md`

**Modified:**
- `api/app/main.py` — mounted payments router
- `frontend/stores/gate.js` — added payment actions and loading state
- `frontend/pages/index.vue` — wired real endpoints, added lookup, shortcuts, modals

**Total lines of code:** ~1,500+ (backend services + routes + schemas + tests + frontend)

---

## Week 5 Exit Criteria

| # | Criterion | Status |
|---|---|---|
| 1 | `POST /api/payments/cash` processes cash payment and publishes `open_gate` | ✅ |
| 2 | `POST /api/payments/rfid` validates member and publishes `open_gate` | ✅ |
| 3 | `POST /api/payments/emoney/deduct` sends deduct command to daemon | ✅ |
| 4 | `POST /api/payments/emoney/result` handles deduct result and updates transaction | ✅ |
| 5 | `POST /api/payments/lookup` finds active transaction by barcode/card/plate | ✅ |
| 6 | Frontend POS calls real endpoints and handles responses | ✅ |
| 7 | All 152+ existing tests pass | ✅ (190 total) |
| 8 | New tests cover all payment flows | ✅ (38 new tests) |
| 9 | No circular imports | ✅ |
| 10 | Documentation written | ✅ |

---

## Looking Ahead to Week 6

**Week 6 scope:** Admin Pages + Device Management
- Full CRUD for settings, devices, members
- Gate configuration UI
- E-money reader management
- Report generation endpoints

*End of Week 5 Build Log*
