# POS Exit Gate — Redesigned Frontend Design

**Date:** 2026-05-07
**Status:** Approved
**Scope:** Exit gate operator POS only (`frontend/pages/index.vue`)

---

## Overview

Redesign the exit gate POS to give operators better tools, clearer information, and faster workflows. The current POS (699 lines, single-page) has critical bugs, missing features, and insufficient information density for real-world booth operations.

### Design Goals
1. **Fix all existing bugs** — vehicleTypes not loaded, no real-time duration, e-money stubs, misleading button text
2. **Add photo comparison** — Entry and exit photos side-by-side for vehicle verification
3. **Add hardware visibility** — Real-time status indicators for controller, e-money, printer, camera, WebSocket
4. **Add quick actions** — Context-aware buttons for stuck vehicles (timeout, insufficient balance, lost contact)
5. **Polish the layout** — Dark theme, better visual hierarchy, quick-denomination cash buttons, sound feedback

### Non-Goals
- Entry gate monitor redesign (separate page: `gate-in.vue`)
- Transaction history page redesign (separate page: `transaksi.vue`)
- Admin pages redesign
- Backend API changes (use existing endpoints)

---

## Layout Architecture

Target resolution: **1920x1080**, dark theme, single monitor.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STATUS BAR (60px fixed height)                                                 │
│  [Gate Code] [Hardware Indicators] [Shift Counter] [Operator Name]              │
├────────────────────────────────────────┬────────────────────────────────────────┤
│                                        │                                        │
│  VEHICLE INFO CARD (60% width)         │  PAYMENT PANEL (40% width)             │
│  - Entry/Exit photos side-by-side      │  - Payment method buttons              │
│  - Vehicle details (plate, type, etc.) │  - Cash modal with quick denominations │
│  - Real-time duration + timeout bar    │  - E-Money status card                 │
│  - Quick actions (conditional)         │  - Barcode scanner input               │
│                                        │                                        │
├────────────────────────────────────────┴────────────────────────────────────────┤
│  QUICK ACTION BAR (50px fixed height)                                           │
│  [Keyboard shortcuts] [Current state text] [Live clock]                         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### CSS Grid Layout
```css
.pos-container {
  display: grid;
  grid-template-rows: 60px 1fr 50px;
  grid-template-columns: 1fr;
  height: 100vh;
}

.main-area {
  display: grid;
  grid-template-columns: 3fr 2fr;  /* 60/40 split */
  gap: 16px;
  padding: 16px;
  overflow: hidden;
}
```

---

## Section 1: Status Bar

**Height:** 60px, fixed, dark background (`#1a1a2e`), bottom border (`#2a2a4a`).

### Left Zone: Gate Identity
- Gate code badge (e.g., `GOUT-01`) — large, bold, color-coded by direction
- Gate name subtitle (e.g., "Gerbang Keluar Utama")

### Center Zone: Hardware Indicators
Five pill-shaped indicators, each showing status dot + label:

| Indicator | Data Source | States |
|-----------|-------------|--------|
| Controller | Daemon heartbeat (`is_online`, `last_heartbeat`) | 🟢 Online (<60s), 🟡 Stale (60-120s), 🔴 Offline (>120s) |
| E-Money | `hardware_config.emoney.enabled` + heartbeat | 🟢 Ready, 🔴 Disabled/Offline |
| Printer | `GET /api/printers/status/summary` (poll every 60s) | 🟢 >50%, 🟡 10-50%, 🔴 <10% or empty |
| Camera | `hardware_config.camera.enabled` + snapshot status | 🟢 Active, 🔴 Disconnected |
| WebSocket | `$ws.isConnected(gateId)` | 🟢 Connected, 🟡 Reconnecting, 🔴 Disconnected |

**Interaction:** Clicking any indicator shows a tooltip with:
- Last heartbeat timestamp
- Error message (if any)
- "Last checked: X seconds ago"

### Right Zone: Shift & Operator
- Shift name + time range (e.g., "Pagi (06:00-14:00)")
- Cash collected this shift: `Rp 1.250.000` (from completed CASH transactions)
- Transaction count: `(42 tx)`
- Operator name + role badge

**Data:** Shift counter computed from `GET /api/transactions?date_from=today&payment_method=CASH&status=COMPLETED`. Cache and increment locally after each cash payment.

---

## Section 2: Vehicle Info Card (Left Panel)

### Photo Comparison Area

Two equal-width photo panels with labels:

```
┌──────────────────────┬──────────────────────┐
│  MASUK (14:30)       │  KELUAR (16:45)      │
│                      │                      │
│  [Entry Snapshot]    │  [Exit Snapshot]     │
│                      │                      │
│  GIN-01              │  GOUT-01             │
└──────────────────────┴──────────────────────┘
```

**Behavior:**
- Entry photo: loaded from `transaction.entry_snapshot_id` → fetch image URL from API
- Exit photo: captured when vehicle triggers IN1 sensor at exit (via `vehicle_detected` WS event → API takes snapshot → stores as `exit_snapshot_id`)
- If no exit photo yet: show placeholder with camera icon + "Menunggu foto..."
- If no entry photo: show placeholder with "Foto masuk tidak tersedia"
- Both photos are clickable → opens full-screen comparison modal with zoom
- Photos auto-refresh when `cameraSnapshot` updates in gate store

**API for snapshots:** Check if `GET /api/snapshots/{id}/image` exists. If not, snapshots are served as static files from the media directory. Use the `file_path` field from the Snapshot model.

### Vehicle Details

Below the photos, a details section:

```
┌──────────────────────────────────────────────────┐
│  🚗 B 1234 ABC                          [🔍]     │
│  Golongan I (Mobil)                              │
│  ─────────────────────────────────────────────── │
│  Durasi    │ 2 jam 15 menit                      │
│  Tarif     │ Rp 10.000                           │
│  Masuk     │ 14:30 — GIN-01                      │
│  Status    │ Menunggu pembayaran                 │
│  ─────────────────────────────────────────────── │
│  ⏱️ 01:45 / 02:00  [████████░░] 85%             │
└──────────────────────────────────────────────────┘
```

**Fields:**
- **Plate number**: Large font (24px), monospace, prominent. From `transaction.plate_number`
- **Vehicle type**: `vehicleTypeName` computed from `transaction.vehicle_type_id` → `websiteStore.vehicleTypes`. Fix: ensure `vehicleTypes` is loaded in `loadAll()`
- **Duration**: Real-time counter. Computed from `entry_time` to `now`. Updates every 1 second via `setInterval`
- **Tariff**: Calculated fee from API (`POST /api/payments/lookup` response or `vehicle_detected` WS event)
- **Entry time + gate**: Formatted `entry_time` + `gate_in_name`
- **Status**: Derived from `paymentState` (IDLE, VEHICLE_PRESENT, WAITING_PAYMENT, TIMEOUT_ALERT)
- **Timeout bar**: Progress bar showing `waitingSeconds / payment_timeout_seconds` (default 120s). Color: green (<75%), orange (75-90%), red (>90%), flashing (100%)

### Quick Actions (Conditional)

Only visible when `paymentState === 'TIMEOUT_ALERT'` or `emoneyPaymentState` is in an error state:

```
┌──────────────────────────────────────────────────┐
│  ⚠️ Kendala: {error_message}                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ 💵 Cash  │ │ 🔄 Retry │ │ ↪️ Skip   │         │
│  └──────────┘ └──────────┘ └──────────┘         │
└──────────────────────────────────────────────────┘
```

**Actions by scenario:**

| Scenario | Actions |
|----------|---------|
| Timeout | [Manual Open] [Reset Gate] [Vehicle Left] |
| E-Money Insufficient | [Pay Cash] [Pay RFID] [Retry E-Money] |
| E-Money Wrong Card | [Retry] [Pay Cash] [Pay RFID] |
| E-Money Lost Contact | [Retry] [Cancel Correction] |
| E-Money Failed | [Retry] [Pay Cash] [Override] |

---

## Section 3: Payment Panel (Right Panel)

### State: Idle (no vehicle)

```
┌────────────────────────────────┐
│     🚧 Palang Keluar           │
│                                │
│     Menunggu kendaraan...      │
│                                │
│     ─────────────────────      │
│     Shortcut:                  │
│     F1: Cash  F2: RFID         │
│     F3: E-Money                │
└────────────────────────────────┘
```

### State: Vehicle Waiting Payment

Three large payment method buttons stacked vertically:

```
┌────────────────────────────────┐
│  Metode Pembayaran             │
│  Total: Rp 10.000              │
│  ─────────────────────────     │
│  ┌──────────────────────────┐  │
│  │  💵                      │  │
│  │  CASH                    │  │
│  │  Bayar tunai             │  │
│  └──────────────────────────┘  │
│  ┌──────────────────────────┐  │
│  │  🪪                      │  │
│  │  RFID                    │  │
│  │  Kartu member            │  │
│  └──────────────────────────┘  │
│  ┌──────────────────────────┐  │
│  │  💳                      │  │
│  │  E-MONEY                 │  │
│  │  Tap kartu e-money       │  │
│  └──────────────────────────┘  │
│                                │
│  ┌──────────────────────────┐  │
│  │  📷 Scan barcode:        │  │
│  │  [___________________]   │  │
│  └──────────────────────────┘  │
└────────────────────────────────┘
```

**Button behavior:**
- **Cash**: Opens cash payment modal
- **RFID**: Opens RFID input modal (or auto-processes if card read via Wiegand)
- **E-Money**: Sends deduct command via booth bridge WebSocket → shows e-money status card
- Buttons are disabled when `awaitingGateOpen === true`
- Keyboard shortcuts: F1, F2, F3

### Cash Payment Modal

```
┌────────────────────────────────────────────────┐
│  💵 Pembayaran Cash                     [✕]    │
│  ────────────────────────────────────────────  │
│  Tarif: Rp 10.000                              │
│                                                │
│  Uang Diterima:                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Rp 10K   │ │ Rp 15K   │ │ Rp 20K   │       │
│  └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Rp 50K   │ │ Rp 100K  │ │ Rp 200K  │       │
│  └──────────┘ └──────────┘ └──────────┘       │
│                                                │
│  Atau masukkan manual:                         │
│  ┌──────────────────────────────────────────┐  │
│  │  Rp 20.000                               │  │
│  └──────────────────────────────────────────┘  │
│  ────────────────────────────────────────────  │
│  Kembalian: Rp 10.000                          │
│                                                │
│  [Batal (Esc)]    [Konfirmasi (Enter)]         │
└────────────────────────────────────────────────┘
```

**Quick denomination buttons:**
- Generated dynamically based on tariff: exact amount, next common denominations
- Denominations: Rp 10.000, 15.000, 20.000, 50.000, 100.000, 200.000
- Only show denominations >= tariff
- Clicking a button fills the manual input and calculates change
- If `paid < tariff`: show error "Uang kurang Rp X"
- Enter key confirms payment

**On confirm:**
1. `POST /api/payments/cash` with `{gate_id, gate_out_id, paid_amount}`
2. Response includes `receipt_queued: true`
3. Set `awaitingGateOpen = true`
4. Show "Struk sedang dicetak..." status
5. Show "Buka Palang" button (or press Space)

### E-Money Status Card

Replaces payment buttons when e-money flow is active:

```
┌────────────────────────────────┐
│  💳 E-Money                    │
│  ─────────────────────────     │
│  Mandiri eMoney                │
│  **** **** **** 1234           │
│  ─────────────────────────     │
│  ⏳ Memproses pembayaran...    │
│  [████████████░░░░░░]          │
│                                │
│  [Batal]                       │
└────────────────────────────────┘
```

**State map:**

| State | Display | Actions |
|-------|---------|---------|
| `WAITING_CARD` | "Tempelkan kartu e-money" | [Batal] |
| `PROCESSING` | "Memproses pembayaran..." + spinner | [Batal] |
| `LOST_CONTACT` | "Proses koreksi... Tempelkan kartu lagi" | [Batal] |
| `WRONG_CARD` | "Gunakan kartu sebelumnya" | [Batal] [Pay Cash] [Pay RFID] |
| `INSUFFICIENT` | "Saldo tidak cukup. Saldo: Rp X" | [Pay Cash] [Pay RFID] [Retry] |
| `SUCCESS` | "Pembayaran berhasil ✓\nSaldo: Rp X" | Auto-clear in 3s |
| `FAILED` | "Transaksi gagal" | [Retry] [Pay Cash] [Pay RFID] |

**Fix from current code:** Implement actual `payCash()` and `payRfid()` transitions (currently stubs in `EmoneyPaymentStatus.vue`).

### After Cash Payment (Awaiting Gate Open)

```
┌────────────────────────────────┐
│  ✅ Pembayaran Berhasil        │
│  Rp 10.000 — Cash              │
│  ─────────────────────────     │
│  Struk sedang dicetak...       │
│  Kembalian: Rp 10.000          │
│  ─────────────────────────     │
│  Tekan SPACE atau klik untuk   │
│  membuka palang                │
│                                │
│  ┌──────────────────────────┐  │
│  │  🔓 BUKA PALANG          │  │
│  └──────────────────────────┘  │
└────────────────────────────────┘
```

**Fix from current code:** Change button text from "Buka Palang & Cetak Struk" to "Buka Palang". Receipt printing is already queued by the cash payment API call, not by the gate open action.

---

## Section 4: Quick Action Bar

**Height:** 50px, fixed, dark background (`#1a1a2e`), top border (`#2a2a4a`).

### Left: Keyboard Shortcuts

Five labeled buttons showing active shortcuts:
- `[F1 💵 Cash]` — disabled when not in WAITING_PAYMENT state
- `[F2 🪪 RFID]` — disabled when not in WAITING_PAYMENT state
- `[F3 💳 E-Money]` — disabled when not in WAITING_PAYMENT state
- `[Space 🔓 Open Gate]` — enabled only when `awaitingGateOpen === true`
- `[Esc ✖ Cancel]` — always enabled (closes modals, resets state)

### Center: State Text

Shows current system state in human-readable Indonesian:
- "Siap" — idle, no vehicle
- "Kendaraan terdeteksi" — vehicle present, transaction loading
- "Menunggu pembayaran" — waiting for operator to process payment
- "Memproses e-money..." — e-money deduct in progress
- "Membuka palang..." — gate open command sent
- "⚠️ Timeout — butuh intervensi" — payment timeout alert

### Right: Live Clock

- Format: `HH:MM:SS`
- Updates every second via `setInterval`

---

## Section 5: Dark Theme

### Color Palette

```css
:root {
  /* Backgrounds */
  --bg-primary: #0f0f23;       /* Main background */
  --bg-secondary: #1a1a2e;     /* Cards, panels */
  --bg-tertiary: #252542;      /* Inputs, buttons */
  --bg-hover: #2a2a4a;         /* Hover states */

  /* Text */
  --text-primary: #e8e8f0;     /* Main text */
  --text-secondary: #a0a0b8;   /* Labels, subtitles */
  --text-muted: #6a6a82;       /* Disabled, placeholders */

  /* Accents */
  --accent-green: #00d68f;     /* Success, online */
  --accent-orange: #ffaa00;    /* Warning, stale */
  --accent-red: #ff3d71;       /* Error, offline */
  --accent-blue: #3366ff;      /* Primary action */
  --accent-purple: #aa66ff;    /* E-money */

  /* Payment methods */
  --cash-color: #00d68f;
  --rfid-color: #3366ff;
  --emoney-color: #aa66ff;

  /* Borders */
  --border-color: #2a2a4a;
  --border-active: #3366ff;
}
```

### Element Plus Overrides

Override Element Plus CSS variables to match dark theme:
```css
:root {
  --el-bg-color: var(--bg-secondary);
  --el-text-color-primary: var(--text-primary);
  --el-border-color: var(--border-color);
  --el-fill-color-blank: var(--bg-tertiary);
}
```

---

## Section 6: Sound Feedback

Use Web Audio API (no external files needed). Generate tones programmatically:

```javascript
// composables/useSound.js
export function useSound() {
  const audioCtx = new AudioContext()

  function playTone(frequency, duration, type = 'sine') {
    const oscillator = audioCtx.createOscillator()
    const gainNode = audioCtx.createGain()
    oscillator.connect(gainNode)
    gainNode.connect(audioCtx.destination)
    oscillator.frequency.value = frequency
    oscillator.type = type
    gainNode.gain.value = 0.1
    oscillator.start()
    oscillator.stop(audioCtx.currentTime + duration)
  }

  return {
    vehicleDetected: () => playTone(800, 0.1),
    paymentSuccess: () => {
      playTone(523, 0.15)  // C5
      setTimeout(() => playTone(659, 0.15), 150)  // E5
    },
    paymentFailed: () => {
      playTone(330, 0.2)  // E4
      setTimeout(() => playTone(262, 0.3), 200)  // C4
    },
    gateOpen: () => playTone(880, 0.2),
    timeoutAlert: () => {
      playTone(440, 0.1)
      setTimeout(() => playTone(440, 0.1), 200)
      setTimeout(() => playTone(440, 0.1), 400)
    },
  }
}
```

**Trigger points:**
- `vehicle_detected` WS event → `vehicleDetected()`
- Cash/RFID/E-Money success → `paymentSuccess()`
- Payment failed/insufficient → `paymentFailed()`
- Gate open command sent → `gateOpen()`
- Timeout alert → `timeoutAlert()`

---

## Section 7: Bug Fixes

### Bug 1: `vehicleTypes` never loaded
**File:** `frontend/stores/website.js`
**Fix:** Add `fetchVehicleTypes()` to `loadAll()`:
```javascript
async loadAll() {
  this.isLoading = true
  try {
    await Promise.all([
      this.fetchGateIns(),
      this.fetchGateOuts(),
      this.fetchVehicleTypes(),  // ADD THIS
      this.fetchSettings(),
    ])
  } finally {
    this.isLoading = false
  }
}
```

### Bug 2: No real-time duration counter
**File:** `frontend/pages/index.vue`
**Fix:** Add `setInterval` in `onMounted`, clear in `onUnmounted`:
```javascript
let durationInterval
onMounted(() => {
  // ... existing code
  durationInterval = setInterval(() => {
    durationText.value = formatDuration(gateStore.currentTransaction?.entry_time)
  }, 1000)
})
onUnmounted(() => {
  clearInterval(durationInterval)
})
```

### Bug 3: E-money override/fallback buttons are stubs
**File:** `frontend/components/EmoneyPaymentStatus.vue`
**Fix:** Implement actual transitions:
- `payCash()` → set `emoneyPaymentState = IDLE`, trigger cash modal
- `payRfid()` → set `emoneyPaymentState = IDLE`, trigger RFID modal
- `override()` → call `POST /api/gates/{id}/open` with reason "override"

### Bug 4: `balance_before` calculation wrong
**File:** `frontend/stores/gate.js` → `confirmEmoneyPayment()`
**Fix:** Use actual API response data, not `tariff + balanceAfter`:
```javascript
// WRONG:
const balance_before = tariff + balanceAfter

// CORRECT: Use balance_before from booth bridge response or API
```

### Bug 5: Misleading button text
**File:** `frontend/pages/index.vue`
**Fix:** Change "Buka Palang & Cetak Struk" to "Buka Palang". Receipt printing is triggered by the cash payment API, not the gate open action.

### Bug 6: Gate selector visible to admins when auto-assigned
**File:** `frontend/pages/index.vue` → `gateSelectorVisible` computed
**Fix:** Only show gate selector if `!currentPos.value` (no auto-detected booth) OR if the POS has multiple gates assigned.

---

## Section 8: Data Flow

### Vehicle Arrival Flow
```
1. GateOutDaemon detects IN1 → publishes VehicleDetectedEvent
2. API EventConsumer receives event → takes exit snapshot
3. API calculates fee, creates/updates transaction
4. API broadcasts to WebSocket clients on /ws/{gate_code}
5. POS receives event via $ws → gateStore.handleWsEvent()
6. gateStore sets paymentState = WAITING_PAYMENT
7. Vehicle Info Card populates with transaction data
8. Photos: entry from transaction.entry_snapshot_id, exit from new snapshot
```

### Payment Flow (Cash)
```
1. Operator clicks Cash / presses F1
2. Cash modal opens with quick denomination buttons
3. Operator enters/selects amount
4. POST /api/payments/cash → {fee, change_amount, receipt_queued}
5. API sends cash_payment_confirmed to daemon via Redis Streams
6. Daemon wins payment race → waits for open_gate command
7. POS sets awaitingGateOpen = true
8. Receipt prints in background (ARQ worker)
9. Operator presses Space / clicks "Buka Palang"
10. POST /api/gates/{id}/open → API sends open_gate to daemon
11. Daemon opens gate → STATE_OPENING
12. Vehicle passes → STATE_IDLE → POS resets
```

### Payment Flow (E-Money via Booth Bridge)
```
1. Driver taps card at booth reader
2. POS sends "emoney_deduct" via WebSocket to booth bridge (ws://localhost:5678)
3. Booth Bridge sends PASSTI deduct frame to serial reader
4. Booth Bridge parses response → calls POST /api/payments/emoney/booth-result (with X-API-Key)
5. API creates EmoneyTransaction → sends emoney_payment_confirmed to daemon
6. API sends open_gate command (auto-open for e-money)
7. Daemon opens gate
8. POS receives success → shows balance → auto-clears in 3s
```

### Hardware Status Polling
```
1. onMounted: GET /api/printers/status/summary → initial paper levels
2. setInterval (60s): poll again → update printer indicator
3. WebSocket heartbeat events: update controller/camera/e-money status
4. WS connection state: update WebSocket indicator in real-time
```

---

## Section 9: Component Structure

### New/Modified Files

| File | Action | Purpose |
|------|--------|---------|
| `frontend/pages/index.vue` | **Rewrite** | Main POS page — new 3-zone layout |
| `frontend/stores/gate.js` | **Modify** | Add real-time duration, fix vehicleTypes, fix e-money stubs |
| `frontend/stores/website.js` | **Modify** | Add `fetchVehicleTypes()` to `loadAll()` |
| `frontend/components/EmoneyPaymentStatus.vue` | **Modify** | Implement payCash/payRfid/override, add balance display |
| `frontend/components/pos/StatusBar.vue` | **New** | Hardware indicators, shift counter, operator info |
| `frontend/components/pos/VehicleInfoCard.vue` | **New** | Photo comparison, vehicle details, timeout bar |
| `frontend/components/pos/PaymentPanel.vue` | **New** | Payment buttons, cash modal, e-money status |
| `frontend/components/pos/QuickActionBar.vue` | **New** | Keyboard shortcuts, state text, live clock |
| `frontend/components/pos/PhotoComparison.vue` | **New** | Side-by-side photo viewer with zoom modal |
| `frontend/components/pos/QuickActions.vue` | **New** | Context-aware action buttons for stuck vehicles |
| `frontend/composables/useSound.js` | **New** | Web Audio API sound feedback |
| `frontend/composables/useHardwareStatus.js` | **New** | Poll printer status, aggregate hardware health |

### Gate Store Additions

```javascript
// New state
const durationSeconds = ref(0)
const hardwareStatus = ref({
  controller: { status: 'unknown', lastHeartbeat: null },
  emoney: { status: 'unknown', enabled: false },
  printer: { status: 'unknown', paperPercent: 0 },
  camera: { status: 'unknown', enabled: false },
  websocket: { status: 'unknown' },
})

// New actions
function startDurationTimer() {
  durationInterval = setInterval(() => {
    if (currentTransaction.value?.entry_time) {
      const entry = new Date(currentTransaction.value.entry_time)
      durationSeconds.value = Math.floor((Date.now() - entry.getTime()) / 1000)
    }
  }, 1000)
}

function stopDurationTimer() {
  clearInterval(durationInterval)
  durationSeconds.value = 0
}

async function refreshHardwareStatus() {
  const response = await fetchApi('/api/printers/status/summary')
  // Map response to hardwareStatus
}
```

---

## Section 10: API Endpoints Used

| Endpoint | Method | Purpose | Frequency |
|----------|--------|---------|-----------|
| `/api/pos/by-ip` | GET | Auto-detect booth on startup | Once |
| `/api/gates?direction=OUT` | GET | Load exit gate list | Once |
| `/api/vehicle-types` | GET | Load vehicle types | Once (fix: was missing) |
| `/api/auth/me` | GET | Verify user session | Once |
| `/api/payments/lookup` | POST | Look up transaction by barcode/plate | On barcode scan |
| `/api/payments/cash` | POST | Process cash payment | On cash confirm |
| `/api/payments/rfid` | POST | Process RFID payment | On RFID confirm |
| `/api/payments/emoney/deduct` | POST | Initiate e-money deduct (fallback) | On e-money start |
| `/api/gates/{id}/open` | POST | Open gate after cash/override | On Space/click |
| `/api/printers/status/summary` | GET | Check paper levels | Every 60s |
| `/api/transactions?date_from=today&payment_method=CASH&status=COMPLETED` | GET | Shift cash total | Once + local increment |
| `GET /api/snapshots/{id}` | GET | Fetch snapshot metadata | On transaction load |
| `WS /ws/{gate_code}` | WebSocket | Real-time gate events | Continuous |

---

## Section 11: Keyboard Shortcuts

| Key | Action | Condition |
|-----|--------|-----------|
| `F1` | Open cash modal | `canPayCash === true` |
| `F2` | Start RFID payment | `canPayRfid === true` |
| `F3` | Start e-money payment | `canPayEmoney === true` |
| `Space` | Open gate | `awaitingGateOpen === true` |
| `Escape` | Close modal / cancel payment / reset | Any modal open or payment in progress |
| `Enter` | Confirm cash payment | Cash modal open |

---

## Section 12: Responsive Behavior

- **Minimum resolution:** 1920x1080 (no responsive breakpoints needed — fixed booth hardware)
- **Overflow handling:** Vehicle info card scrolls internally if content exceeds viewport
- **Photo sizing:** Photos maintain 16:9 aspect ratio, scale to fill available width
- **Font sizes:** Minimum 14px for body, 18px for labels, 24px for plate numbers

---

## Section 13: Error Handling

### Network Errors
- API call failures: Show `ElMessage.error()` with retry option
- WebSocket disconnect: Show red indicator in status bar, auto-reconnect (existing plugin handles this)
- Booth bridge disconnect: Show warning, fall back to API-based e-money deduct

### Hardware Errors
- Controller offline: Show alert in status bar, disable payment buttons
- Printer paper empty: Show warning before cash payment, allow override
- Camera disconnected: Show placeholder in photo area, allow payment to proceed

### Transaction Errors
- Transaction not found on lookup: Show "Kendaraan tidak ditemukan" + clear input
- Duplicate payment attempt: Show "Pembayaran sudah diproses" + disable buttons
- Gate open fails: Show error, allow retry, log to audit

---

## Section 14: Testing Checklist

- [ ] Vehicle detection → Vehicle Info Card populates with correct data
- [ ] Entry/exit photos display side-by-side
- [ ] Real-time duration counter updates every second
- [ ] Timeout progress bar changes color at 75%/90%/100%
- [ ] Cash payment with quick denomination buttons
- [ ] Cash payment with manual amount input
- [ ] Cash payment change calculation correct
- [ ] E-money flow: waiting → processing → success/failure states
- [ ] E-money fallback to cash/RFID from error states
- [ ] RFID payment flow
- [ ] Gate open after cash payment (Space/click)
- [ ] Hardware status indicators update correctly
- [ ] Shift counter increments after cash payment
- [ ] Keyboard shortcuts work (F1, F2, F3, Space, Esc, Enter)
- [ ] Sound feedback plays on events
- [ ] vehicleTypes loaded correctly (bug fix #1)
- [ ] Duration timer cleared on unmount (bug fix #2)
- [ ] E-money override/fallback functional (bug fix #3)
- [ ] Button text says "Buka Palang" not "Buka Palang & Cetak Struk" (bug fix #5)
- [ ] Gate selector hidden when auto-assigned (bug fix #6)
- [ ] Dark theme applied consistently across all components
