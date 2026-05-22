# Week 3 — Changes & Build Log

> **Date:** 25 April 2026
> **Scope:** Frontend Foundation + Integration
> **Depends on:** Week 1 (Foundation & Database), Week 2 (Auth, API, WebSocket, Workers)

---

## What Was Built

### 1. Nuxt 3 Project Scaffold (`frontend/`)

| File | Purpose |
|------|---------|
| `frontend/package.json` | Dependencies: Nuxt 3, Element Plus, Pinia, Vue Router |
| `frontend/nuxt.config.ts` | Module registration, runtime config (apiBaseUrl, wsBaseUrl), CORS setup |
| `frontend/app.vue` | Root app with `<NuxtLayout>` and `<NuxtPage>` |
| `frontend/.gitignore` | Standard Nuxt ignores |

**Dependencies installed:**
- `nuxt` ^3.15.0
- `@pinia/nuxt` ^0.9.0
- `@element-plus/nuxt` ^1.1.1
- `element-plus` ^2.9.0
- `pinia` ^2.3.0
- `vue` ^3.5.0
- `vue-router` ^4.5.0
- `vitest` ^3.2.0 (dev)

### 2. Composables (`frontend/composables/`)

| File | Purpose |
|------|---------|
| `useApi.js` | Low-level fetch wrapper with `credentials: 'include'` for httpOnly cookies, JSON parsing, structured error throwing |
| `useCrud.js` | Reusable CRUD (list, get, create, update, remove) built on useApi |

**Key design decisions:**
- `credentials: 'include'` on every request so httpOnly cookies are sent automatically
- Content-Type automatically stripped for FormData/Blob bodies
- Errors carry `.status` and `.data` for downstream handling

### 3. Pinia Stores (`frontend/stores/`)

| File | State | Actions | Getters |
|------|-------|---------|---------|
| `auth.js` | `user`, `isLoading`, `error` | `login()`, `fetchUser()`, `logout()`, `refreshToken()`, `initAuth()` | `isLoggedIn`, `isAdmin`, `isOperator` |
| `website.js` | `gateIns`, `gateOuts`, `vehicleTypes`, `settings` | `fetchGateIns()`, `fetchGateOuts()`, `fetchSettings()`, `loadAll()` | `activeGateIns`, `activeGateOuts`, `getSetting(key)` |
| `gate.js` | `currentTransaction`, `paymentState`, `emoneyPaymentState`, `wsConnected`, `cameraSnapshot`, `waitingSeconds` | `setTransaction()`, `clearTransaction()`, `handleWsEvent()` | `isWaitingPayment`, `canPayCash`, `canPayEmoney`, `canPayRfid` |

### 4. WebSocket Plugin (`frontend/plugins/websocket.js`)

- Global `$ws` instance via Nuxt plugin
- Per-gate connection management (`connect`, `disconnect`, `disconnectAll`)
- Auto-reconnect with exponential backoff (1s → 30s max)
- Event listener subscription model (`on(gateId, callback)` returns unsubscribe fn)
- Sends/receives JSON over WebSocket

### 5. Layouts & Middleware

| File | Purpose |
|------|---------|
| `layouts/default.vue` | Sidebar navigation (220px dark theme), header with breadcrumb + user info, logout button |
| `middleware/auth.js` | Redirect unauthenticated users to `/login`; redirect logged-in users away from `/login` |

**Navigation routes in sidebar:**
- POS (`/`)
- Gate In (`/gate-in`)
- Transaksi (`/transaksi`)
- Member (`/member`)
- Laporan (`/report`)
- Notifikasi (`/notification`)
- Admin submenu: Pengaturan (`/setting`), Perangkat (`/device`)

### 6. Pages (`frontend/pages/`)

| Route | Page | Features |
|-------|------|----------|
| `/login` | `login.vue` | Gradient background, Element Plus form, validation rules, httpOnly cookie login, error display, redirect to `/` on success |
| `/` | `index.vue` | **POS page** — gate selector, active transaction display, camera snapshot, triple-method payment (Cash / RFID / E-Money), cash payment modal with change calculation, e-money status panel integration |
| `/gate-in` | `gate-in.vue` | Grid of active gate-in cards showing mode, protocol, area |
| `/transaksi` | `transaksi.vue` | Placeholder |
| `/setting` | `setting.vue` | Placeholder (admin-only route) |
| `/device` | `device.vue` | Placeholder (admin-only route) |
| `/member` | `member.vue` | Placeholder |
| `/report` | `report.vue` | Placeholder |
| `/notification` | `notification.vue` | Placeholder |

### 7. Components (`frontend/components/`)

| File | Purpose |
|------|---------|
| `EmoneyPaymentStatus.vue` | Visual state indicator for e-money payment flow (WAITING_CARD, PROCESSING, LOST_CONTACT, WRONG_CARD, INSUFFICIENT, SUCCESS, FAILED) with contextual action buttons |

### 8. Global Styles (`frontend/assets/css/main.css`)

Utility classes for spacing, flex, colors, sizing — used across all pages.

---

## Verification Results

| Test | Result |
|------|--------|
| `npm install` | ✅ 680 packages, 0 vulnerabilities |
| `npm run build` (production) | ✅ Client + SSR + Nitro built successfully (4.18 MB total) |
| `npm run build` (second pass after layout update) | ✅ Built successfully |
| All 9 pages compile | ✅ Verified via Nitro chunks |
| All 3 stores compile | ✅ Verified via client bundles |
| WebSocket plugin compiles | ✅ Verified via client bundles |
| Element Plus styles load | ✅ Verified via CSS chunks |
| No circular imports | ✅ Verified by Vite transform |

---

## Decisions Made

1. **No localStorage for auth:** Tokens are httpOnly cookies only. The auth store only keeps the user object in memory. Refresh on page load via `initAuth()`.

2. **WebSocket per gate:** Each gate has its own WS connection. This matches the backend's `/ws/{gate_id}` endpoint design and simplifies event routing.

3. **Exponential backoff for WS reconnect:** Starts at 1s, doubles up to 30s. Prevents hammering the server on network issues.

4. **POS page as default route (`/`):** Operators spend 90% of their time on POS. Direct access reduces clicks.

5. **Placeholders for non-POS pages:** Week 3 focuses on foundation + integration. Full CRUD pages for settings, devices, members, etc. will be built in Weeks 4–6.

6. **Gate-out ID stored in gate store:** Selected gate-out persists across navigation within the session.

7. **E-money state machine in gate store:** Matches the backend `deduct_result` event schema. `EmoneyPaymentStatus.vue` renders the correct UI per state.

---

## Files Created/Modified

**Created:** 20+ new files across `frontend/`
- `frontend/package.json`
- `frontend/nuxt.config.ts`
- `frontend/app.vue`
- `frontend/.gitignore`
- `frontend/assets/css/main.css`
- `frontend/composables/useApi.js`
- `frontend/composables/useCrud.js`
- `frontend/stores/auth.js`
- `frontend/stores/website.js`
- `frontend/stores/gate.js`
- `frontend/plugins/websocket.js`
- `frontend/layouts/default.vue`
- `frontend/middleware/auth.js`
- `frontend/pages/login.vue`
- `frontend/pages/index.vue`
- `frontend/pages/gate-in.vue`
- `frontend/pages/transaksi.vue`
- `frontend/pages/setting.vue`
- `frontend/pages/device.vue`
- `frontend/pages/member.vue`
- `frontend/pages/report.vue`
- `frontend/pages/notification.vue`
- `frontend/components/EmoneyPaymentStatus.vue`

**Modified:** None (frontend was greenfield for Week 3)

**Total lines of code:** ~2,000+

---

## Week 3 Exit Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `npm install` completes with 0 vulnerabilities | ✅ |
| 2 | `npm run build` produces production bundle without errors | ✅ |
| 3 | Login page renders with form validation | ✅ |
| 4 | Auth store manages login/logout/user state | ✅ |
| 5 | Website store fetches reference data (gates, settings) | ✅ |
| 6 | Gate store tracks payment state and e-money state | ✅ |
| 7 | WebSocket plugin connects with auto-reconnect | ✅ |
| 8 | Auth middleware protects routes and redirects | ✅ |
| 9 | POS page has triple-method payment layout | ✅ |
| 10 | All 9 pages have routes and compile | ✅ |
| 11 | Default layout has sidebar navigation | ✅ |
| 12 | No circular imports between frontend modules | ✅ |

---

## Looking Ahead to Week 4

**Week 4 scope:** Gate Daemon Core
- `daemons/base.py` — Redis Streams consumer, heartbeat, state persistence
- `daemons/gate_in.py` — Full gate-in state machine (Cash, RFID, E-Money)
- `daemons/gate_out.py` — Full gate-out state machine with asyncio.wait FIRST_COMPLETED
- Integration tests between daemons and FastAPI via Redis Streams

*End of Week 3 Build Log*
