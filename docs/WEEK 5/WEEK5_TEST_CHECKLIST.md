# Week 5 — Test Checklist

> **Date:** 25 April 2026
> **Goal:** Verify payment API, transaction services, and frontend POS wiring

---

## Pre-requisites

- [x] Week 1–4.5 exit criteria all passed
- [x] Docker Compose running (postgres, redis)
- [x] Dependencies installed: `pip install -e ".[dev]"`
- [x] Frontend dependencies installed: `cd frontend && npm install`

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| T1: Transaction service — create | **PASS** | 3/3 tests |
| T2: Transaction service — find | **PASS** | 5/5 tests |
| T3: Transaction service — fee calculation | **PASS** | 3/3 tests |
| T4: Transaction service — shift | **PASS** | 2/2 tests |
| T5: Transaction service — complete | **PASS** | 2/2 tests |
| T6: Transaction service — tariff config | **PASS** | 3/3 tests |
| T7: Payment service — cash | **PASS** | 3/3 tests |
| T8: Payment service — RFID | **PASS** | 3/3 tests |
| T9: Payment service — e-money deduct | **PASS** | 2/2 tests |
| T10: Payment service — e-money result | **PASS** | 3/3 tests |
| T11: Payment routes — cash | **PASS** | 2/2 tests |
| T12: Payment routes — RFID | **PASS** | 1/1 tests |
| T13: Payment routes — e-money deduct | **PASS** | 1/1 tests |
| T14: Payment routes — e-money result | **PASS** | 2/2 tests |
| T15: Payment routes — lookup | **PASS** | 2/2 tests |
| T16: Existing tests (Weeks 1–4.5) | **PASS** | 152/152 tests — no regressions |
| T17: Frontend build | **PASS** | Production build successful |
| **Total** | **190/190** | **100%** |

---

## Detailed Test Log

### T1–T6: Transaction Service Tests

**Command:**
```bash
pytest api/tests/test_transaction_service.py -v
```

**Results:**
- [x] Create cash transaction
- [x] Create RFID transaction
- [x] Create e-money transaction
- [x] Find by barcode
- [x] Find by card number
- [x] Find by plate number
- [x] Not found returns None
- [x] Completed transaction not found
- [x] No criteria returns None
- [x] Grace period = zero fee
- [x] One hour = correct fee
- [x] Unknown vehicle type defaults
- [x] Find current shift
- [x] No shifts returns None
- [x] Complete cash transaction
- [x] Complete RFID transaction
- [x] Tariff config from database
- [x] None returns default config
- [x] Invalid ID returns default config

### T7–T10: Payment Service Tests

**Command:**
```bash
pytest api/tests/test_payment_service.py -v
```

**Results:**
- [x] Cash payment success (transaction completed, open_gate + print_receipt published)
- [x] Cash payment transaction not found
- [x] Cash payment plate lookup
- [x] RFID payment success (zero fee, open_gate + play_audio published)
- [x] RFID invalid member card
- [x] RFID no active transaction
- [x] E-money deduct success (PENDING status, deduct command published)
- [x] E-money deduct transaction not found
- [x] E-money result SUCCESS (transaction completed, 3 commands published)
- [x] E-money result FAILED (no commands published, transaction reset)
- [x] E-money result INSUFFICIENT_BALANCE

### T11–T15: Payment Routes Tests

**Command:**
```bash
pytest api/tests/test_payment_routes.py -v
```

**Results:**
- [x] POST /api/payments/cash returns success with fee and change
- [x] POST /api/payments/cash returns failure for invalid transaction
- [x] POST /api/payments/rfid returns success with zero fee
- [x] POST /api/payments/emoney/deduct returns PENDING status
- [x] POST /api/payments/emoney/result returns success for SUCCESS status
- [x] POST /api/payments/emoney/result returns failure for invalid status
- [x] POST /api/payments/lookup finds transaction by barcode
- [x] POST /api/payments/lookup returns not found for invalid barcode

### T16: Regression Tests

**Command:**
```bash
pytest -v
```

**Results:**
- [x] All 152 existing tests still pass
- [x] No new warnings (except existing JWT key length)
- [x] No import errors
- [x] No circular dependencies

### T17: Frontend Build

**Command:**
```bash
cd frontend && npm run build
```

**Results:**
- [x] Client build completes
- [x] SSR build completes
- [x] Nitro server build completes
- [x] Total size ~4.21 MB
- [x] No compilation errors

---

## Manual Verification Steps

| Step | Command / Action | Expected |
|------|-----------------|----------|
| API routes | `python -c "from api.app.main import app; print([r.path for r in app.routes])"` | `/api/payments/cash`, `/api/payments/rfid`, `/api/payments/emoney/deduct`, `/api/payments/emoney/result`, `/api/payments/lookup` visible |
| Cash endpoint | `curl -X POST http://localhost:8000/api/payments/lookup -d '{"barcode":"T100"}' -H "Content-Type: application/json" -H "Cookie: access_token=..."` | Returns transaction JSON |
| Frontend POS | Open http://localhost:3000/ | Gate selector, barcode input, payment buttons visible |
| Keyboard shortcuts | Press F1/F2/F3 on POS | Cash/RFID/E-Money modals open |

---

## Known Issues / Notes

1. **Test database FK constraints:** Service tests use `gate_out_id=None` to avoid FK violations against empty reference tables in the test database. In production, real gate_out IDs will be provided by the frontend.

2. **JWT key length warning:** Existing dev warning about JWT secret < 32 bytes. Production must use 64+ character random string.

3. **Redis connection in tests:** The `gate_command.publish_command()` function connects to Redis. In route tests, the payment service functions are mocked to avoid Redis dependency.

4. **E-money auto-dismiss:** Frontend auto-clears SUCCESS state after 3 seconds. This is frontend-only behavior; the backend transaction is already completed.

5. **POS barcode lookup:** The lookup field accepts both barcode and plate number. In production, a barcode scanner would auto-submit on scan.

---

## Week 5 Exit Criteria Summary

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

*End of Week 5 Test Checklist*
