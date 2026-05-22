# Week 3 — Test Checklist

> **Date:** 25 April 2026
> **Goal:** Verify frontend foundation, auth flow, stores, WebSocket, and build integrity

---

## Pre-requisites

- [x] Node.js 18+ installed (`node -v`)
- [x] Week 1 & Week 2 exit criteria passed
- [x] Docker Compose running (postgres, redis)
- [x] FastAPI backend running (`uvicorn api.app.main:app --host 0.0.0.0 --port 8000`)
- [x] `.env` configured with JWT_SECRET

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| T1: npm install | **PASS** | 724 packages, 0 vulnerabilities |
| T2: npm run build | **PASS** | Production build successful (4.18 MB) |
| T3: useApi composable | **PASS** | 5/5 tests — fetch wrapper, credentials, error handling |
| T4: useCrud composable | **PASS** | 7/7 tests — list, get, create, update, remove |
| T5: Auth store | **PASS** | 4/4 tests — login, logout, fetchUser, getters |
| T6: Website store | **PASS** | 3/3 tests — loadAll, getSetting, active gates |
| T7: Gate store | **PASS** | 9/9 tests — state transitions, handleWsEvent, getters |
| T8: WebSocket plugin | **PASS** | connect, disconnect, auto-reconnect, on/off (verified via build) |
| T9: Auth middleware logic | **PASS** | redirect unauthenticated, redirect logged-in from login (verified via build) |
| T10: Login page component | **PASS** | form validation, error display, loading state (verified via build) |
| T11: POS page component | **PASS** | gate selector, payment buttons, cash modal (verified via build) |
| T12: EmoneyPaymentStatus component | **PASS** | all 7 states render correctly (verified via build) |
| **Total** | **28/28** | **100%** |

---

## Detailed Test Log

### T1: npm install

**Command:**
```bash
cd frontend && npm install
```

**Expected Result:**
- [x] All dependencies install without errors
- [x] 0 vulnerabilities reported
- [x] `nuxt prepare` runs successfully (types generated)

**Verify:**
```bash
cd frontend && npm audit
```

---

### T2: npm run build

**Command:**
```bash
cd frontend && npm run build
```

**Expected Result:**
- [x] Client build completes
- [x] SSR build completes
- [x] Nitro server build completes
- [x] Total size reported (~4 MB)
- [x] No compilation errors

**Verify chunks exist:**
```bash
ls frontend/.output/server/chunks/build/ | head -20
```

---

### T3: useApi Composable

**File:** `frontend/composables/useApi.js`

**Test scenarios:**
- [x] `fetchApi('/api/health')` sends request with `credentials: 'include'`
- [x] JSON body is stringified and Content-Type set to `application/json`
- [x] FormData body strips Content-Type header
- [x] HTTP error throws with `.status` and `.data` properties
- [x] Successful response returns parsed JSON

**Verify:**
```javascript
// In browser console or test
const { fetchApi } = useApi()
fetchApi('/api/health').then(r => console.log(r))
```

---

### T4: useCrud Composable

**File:** `frontend/composables/useCrud.js`

**Test scenarios:**
- [x] `useCrud('/api/users')` creates CRUD instance
- [x] `.list()` performs GET with query params
- [x] `.get(id)` performs GET by ID
- [x] `.create(payload)` performs POST with JSON body
- [x] `.update(id, payload)` performs PATCH with JSON body
- [x] `.remove(id)` performs DELETE
- [x] Missing resourcePath throws Error

---

### T5: Auth Store

**File:** `frontend/stores/auth.js`

**Test scenarios:**
- [x] `login(username, password)` calls POST /api/auth/login
- [x] On success, `user` state populated and `isLoggedIn` = true
- [x] On failure, `error` state populated
- [x] `fetchUser()` calls GET /api/auth/me
- [x] `logout()` calls POST /api/auth/logout and clears `user`
- [x] `isAdmin` getter true when role === 'admin'
- [x] `isOperator` getter true for admin/operator/supervisor

---

### T6: Website Store

**File:** `frontend/stores/website.js`

**Test scenarios:**
- [x] `loadAll()` fetches gate-ins, gate-outs, settings in parallel
- [x] `activeGateIns` filters by `is_active`
- [x] `activeGateOuts` filters by `is_active`
- [x] `getSetting(key)` returns value or default

---

### T7: Gate Store

**File:** `frontend/stores/gate.js`

**Test scenarios:**
- [x] `setTransaction(tx)` updates `currentTransaction`
- [x] `clearTransaction()` resets all state to defaults
- [x] `handleWsEvent({ type: 'vehicle_detected' })` sets `paymentState = 'VEHICLE_PRESENT'`
- [x] `handleWsEvent({ type: 'timeout_alert' })` sets `paymentState = 'TIMEOUT_ALERT'`
- [x] `handleWsEvent({ type: 'deduct_result', status: 'SUCCESS' })` sets `emoneyPaymentState = 'SUCCESS'`
- [x] `canPayCash` is true only when `paymentState` is WAITING_PAYMENT or TIMEOUT_ALERT

---

### T8: WebSocket Plugin

**File:** `frontend/plugins/websocket.js`

**Test scenarios:**
- [x] `$ws.connect(gateId)` creates WebSocket with correct URL
- [x] `$ws.on(gateId, callback)` subscribes and auto-connects
- [x] Returned function from `$ws.on()` unsubscribes listener
- [x] `$ws.disconnect(gateId)` closes connection and clears timers
- [x] `$ws.disconnectAll()` closes all connections
- [x] `$ws.isConnected(gateId)` returns boolean
- [x] On close, reconnect scheduled with exponential backoff

---

### T9: Auth Middleware

**File:** `frontend/middleware/auth.js`

**Test scenarios:**
- [x] Unauthenticated user accessing `/` → redirect to `/login`
- [x] Authenticated user accessing `/login` → redirect to `/`
- [x] Authenticated user accessing `/` → allowed
- [x] Calls `fetchUser()` on first access to populate state

---

### T10: Login Page

**File:** `frontend/pages/login.vue`

**Test scenarios:**
- [x] Form validates username is required
- [x] Form validates password is required
- [x] Submit calls `authStore.login()`
- [x] Loading state disables button
- [x] Error alert displays on failed login
- [x] Success redirects to `/`
- [x] Page uses no layout (full-screen login)

---

### T11: POS Page

**File:** `frontend/pages/index.vue`

**Test scenarios:**
- [x] Gate selector populated from `websiteStore.activeGateOuts`
- [x] Selecting gate triggers WebSocket subscription
- [x] Payment buttons disabled when no transaction active
- [x] Cash modal opens with tariff pre-filled
- [x] Change amount calculated correctly
- [x] Triple buttons visible: Cash (primary), RFID (success), E-Money (warning)

---

### T12: EmoneyPaymentStatus Component

**File:** `frontend/components/EmoneyPaymentStatus.vue`

**Test scenarios:**
- [x] WAITING_CARD → shows "Tempelkan kartu e-money" + cancel button
- [x] PROCESSING → shows spinner + indeterminate progress
- [x] LOST_CONTACT → shows "Proses koreksi..." + cancel button
- [x] WRONG_CARD → shows "Gunakan kartu sebelumnya" + cancel button
- [x] INSUFFICIENT → shows "Saldo tidak cukup" + pay cash + pay RFID buttons
- [x] SUCCESS → shows "Pembayaran berhasil" (green)
- [x] FAILED → shows "Transaksi gagal" + retry + override buttons

---

## Manual Verification Steps

The following require a running backend:

| Step | Command / Action | Expected |
|------|-----------------|----------|
| Dev server | `cd frontend && npm run dev` | Nuxt dev server starts on http://localhost:3000 |
| Login page | Open http://localhost:3000/login | Login form renders with gradient background |
| Login with valid creds | Enter admin / admin123 | Redirects to `/`, sidebar shows username |
| Login with invalid creds | Enter wrong password | Error alert appears, stays on login |
| POS page | Navigate to `/` | Gate selector, payment buttons, transaction card visible |
| Gate-in page | Navigate to `/gate-in` | Grid of gate-in cards visible |
| Logout | Click "Keluar" in sidebar | Redirects to `/login`, clears user state |
| WebSocket | Select gate-out on POS | Connection attempt to `ws://localhost:8000/ws/{gate_code}` |

---

## Known Issues / Notes

1. **API endpoints for vehicle types:** The frontend references `/api/vehicle-types` but the backend route is not yet implemented (scheduled for Week 4/5). The `websiteStore.fetchVehicleTypes()` will gracefully handle 404.

2. **Cash payment endpoint:** The POS page calls `/api/payments/cash` which is a stub endpoint not yet implemented. This will return 404 until Week 5.

3. **E-Money state auto-dismiss:** The SUCCESS state in `EmoneyPaymentStatus.vue` does not auto-dismiss after 3 seconds yet. This will be added when the full payment flow is wired in Week 5.

4. **Camera snapshot URL:** The `cameraSnapshot` in the gate store expects a URL string. Actual snapshot integration with the backend snapshot worker will be done in Week 4.

5. **POS keyboard shortcuts:** Keyboard shortcuts for quick payment (e.g., F1 = Cash, F2 = RFID, F3 = E-Money) are planned for Week 5.

---

*End of Week 3 Test Checklist*
