# POS Redesign Plan — E-Parking v2

> Objective: Redesign the Point of Sale (gate-out operator) page to match the functionality and information density of a professional Indonesian parking POS system.

---

## 1. Current State Assessment

### What Exists Now

The current POS page (`frontend/pages/index.vue`) is a minimal two-column layout:

- **Left column**: Barcode search input, transaction detail table (5 fields), camera snapshot
- **Right column**: Three payment buttons (Cash/RFID/E-Money), e-money status panel, open-gate prompt
- **Single snapshot**: Only shows entry photo, no side-by-side entry+exit comparison
- **Cash modal**: Amount received + change calculator
- **RFID modal**: Card number input
- **WebSocket**: Real-time vehicle detection and payment timeout alerts

### What's Missing

| Category | Gap |
|----------|-----|
| **Context** | No site name, shift info, operator name, live clock |
| **Occupancy** | No parking area capacity/availability display |
| **Transaction detail** | No tariff breakdown, no gate-in name, no member info, no vehicle type icon |
| **Dual snapshots** | No side-by-side entry/exit photo comparison for vehicle verification |
| **Lost ticket** | No lost-ticket flow (backend supports `is_lost_ticket` + `lost_ticket_penalty`) |
| **Gate control** | Manual open/close only available post-payment, no sensor status, no controller/reader health |
| **Daily summary** | No running revenue/transaction count for current shift |
| **Alerts** | No hardware alerts, no reader offline warning, no unresolved alert badge |
| **Recent transactions** | No mini-list of recent exits |
| **Receipt reprint** | No UI to re-trigger receipt printing |
| **Keyboard workflow** | Only F1/F2/F3/Space/Escape — missing F4 (lost ticket), F5 (manual open), F6 (reprint) |
| **Auto-lookup** | Vehicle detection event doesn't auto-populate transaction |

---

## 2. Screen Layout — Section Map

```
┌──────────────────────────────────────────────────────────────────────┐
│ [HEADER BAR]  Site Name │ Shift │ Operator │ Clock │ Gate Selector   │
│               │ Gate Status ● │ Booth ● │ Alerts ⚠ 3                    │
├──────────────────────┬───────────────────────────────────────────────┤
│                      │  TRANSACTION DETAIL                           │
│  PARKING AREA        │  ┌─────────────────────────────────────────┐  │
│  ┌────────────────┐  │  │ Barcode: XXXX   │ Status: ACTIVE ●     │  │
│  │ Basement A      │  │  │ Card: •••4521   │ Method: —             │  │
│  │ ████████░░ 34   │  │  │ Plate: B 1234AB│ Duration: 2j 15m ↑    │  │
│  │ 34 / 50 slot   │  │  │ Type: 🚗 Mobil  │ Entry: 14:30, Gate GIN01│  │
│  │                 │  │  ├─────────────────────────────────────────┤  │
│  │ 🟢 Available    │  │  │ TARIFF BREAKDOWN                         │  │
│  └────────────────┘  │  │ 1 jam pertama   Rp 5.000                │  │
│                      │  │ 1 jam berikutnya Rp 3.000  ×2 = 6.000  │  │
│  GATE STATUS         │  │ Total tarif      Rp 11.000              │  │
│  ┌────────────────┐  │  │ ────────────────────────────────────    │  │
│  │ Palang: ▲ OPEN  │  │  │  Total       Rp 11.000  ◀◀ large     │  │
│  │ Sensor IN1: ●   │  │  └─────────────────────────────────────────┘  │
│  │ Controller: 🟢  │  │                                               │
│  │ E-Money:    🟢  │  │  SNAPSHOTS (MASUK & KELUAR)                 │
│  │ Heartbeat:  3s  │  │  ┌──────────────────┬──────────────────────┐  │
│  └────────────────┘  │  │  │ 📷 FOTO MASUK     │ 📷 FOTO KELUAR      │  │
│                      │  │  │ [Entry photo]     │ [Exit photo]        │  │
│  QUICK ACTIONS       │  │  │ B 1234AB (92%)    │ B 1234AB (87%)      │  │
│  ┌────────────────┐  │  │  │ 14:30             │ 16:45               │  │
│  │ ▶ Manual Open  │  │  └──────────────────┴──────────────────────┘  │
│  ┌────────────────┐  │                                               │
│  │ ▶ Manual Open  │  │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│  │ ▶ Reprint      │  │  PAYMENT PANEL                               │
│  │ ▶ Display Text │  │  ┌─────────────────────────────────────────┐  │
│  │ ▶ Play Audio   │  │  │ ┌─────────┐ ┌─────────┐ ┌─────────┐    │  │
│  └────────────────┘  │  │ │  TUNAI  │ │  RFID   │ │ E-MONEY │    │  │
│                      │  │ │  (F1)   │ │  (F2)   │ │  (F3)   │    │  │
│  DAILY SUMMARY       │  │ └─────────┘ └─────────┘ └─────────┘    │  │
│  ┌────────────────┐  │  │ ┌─────────┐ ┌─────────────────────┐    │  │
│  │ Transaksi:  47  │  │  │ │ LOST TK │ │   MANUAL OPEN (F5)  │    │  │
│  │ Pendapatan: 2.1M│  │  │ │  (F4)   │ │   Buka palang tanpa │    │  │
│  │ Tunai:    800K   │  │  │ └─────────┘ │   pembayaran        │    │  │
│  │ E-Money:  1.0M  │  │  │             └─────────────────────┘    │  │
│  │ RFID:     300K  │  │  │                                    │  │
│  │ Aktif:    23    │  │  │ [E-Money Status / Open Gate]      │  │
│  └────────────────┘  │  │ [Timeout Alert if applicable]      │  │
│                      │  └─────────────────────────────────────────┘  │
├──────────────────────┴───────────────────────────────────────────────┤
│ [RECENT TRANSACTIONS]  10 terakhir: B1234 Mobil Tunai Rp5K │ ...  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Section Specifications

### 3.1 Header Bar

**Position**: Fixed top bar, always visible

| Element | Data Source | Type | Notes |
|---------|------------|------|-------|
| Site name + logo | `GET /api/site-config` (name, logo_url) | Text + image | Left-aligned |
| Current shift | `GET /api/shifts?is_active=true` → filter by current time | Badge | "Shift Pagi (06:00-14:00)" |
| Operator name | `authStore.user.full_name` | Text | Right side |
| Live clock | `new Date()` with 1s interval | Text | Format: HH:mm:ss, DD MMM YYYY |
| Gate selector | `websiteStore.activeGateOuts` | Dropdown | Only if admin or multi-gate booth |
| Gate online status | `Gate.is_online` + WS `heartbeat` event | Dot + text | 🟢 Online / 🔴 Offline |
| Booth connection | `gateStore.boothConnected` | Dot + text | Already implemented |
| Unresolved alerts | `GET /api/audit-logs?is_resolved=false` or WS push | Badge count | Red badge, clickable |

### 3.2 Parking Area Status

**Position**: Left sidebar, top

| Element | Data Source | Type | Notes |
|---------|------------|------|-------|
| Area name | `Gate.area_parkir.name` | Text | Linked to selected gate's area |
| Capacity | `AreaParkir.capacity` | Number | Total parking slots |
| Current occupancy | `AreaParkir.current` | Number | Live count (updated via WS) |
| Available slots | `capacity - current` | Computed | Large, green number |
| Occupancy bar | `(current / capacity) * 100` | Progress bar | Green (<60%), Yellow (60-85%), Red (>85%) |

**Real-time update**: Subscribe to vehicle_passed / vehicle_detected events to increment/decrement counts. Periodic poll `GET /api/areas` every 60s as fallback.

### 3.3 Gate Status Panel

**Position**: Left sidebar, middle

| Element | Data Source | Type | Notes |
|---------|------------|------|-------|
| Gate state | WS `heartbeat_state.state` | Badge | IDLE (gray), VEHICLE_PRESENT (yellow), WAITING_PAYMENT (orange), OPENING (green) |
| Sensor states | WS `heartbeat_state.state_data` | Indicators | IN1, IN2, IN3, IN4 — active dot or gray |
| Controller status | WS `heartbeat.controller_ok` | Indicator | 🟢 Connected / 🔴 Disconnected |
| E-money reader | WS `heartbeat.passti_ok` | Indicator | 🟢 Online / 🔴 Offline |
| Last heartbeat | WS `heartbeat.timestamp` | Relative time | "3s ago", "45s ago" |
| Manual open button | `POST /api/gates/{id}/open` | Button | Always accessible (reason dropdown) |
| Close gate button | `POST /api/gates/{id}/close` | Button | Only for DUAL relay gates |
| Display text | `display_text` command | Input + send | Two-line LED text, brightness slider |
| Play audio | `play_audio` command | Dropdown | Track number or name selector |

### 3.4 Quick Actions

**Position**: Left sidebar, bottom

| Action | Endpoint | Keyboard | Notes |
|--------|----------|----------|-------|
| Manual gate open | `POST /api/gates/{id}/open` | F5 | With reason: operator, emergency, test |
| Reprint receipt | `POST /api/payments/reprint` (new endpoint needed) | F6 | Re-trigger print for last transaction |
| Display custom text | Redis `display_text` command | — | Two-line input |
| Play audio | Redis `play_audio` command | — | Track dropdown |

### 3.5 Daily Summary

**Position**: Left sidebar, bottom

| Element | Data Source | Type | Notes |
|---------|------------|------|-------|
| Total transactions | `GET /api/reports/summary` | Number | Today's count |
| Total revenue | `SummaryReport.total_revenue` | Formatted IDR | Bold |
| Cash revenue | `SummaryReport.cash_revenue` | Formatted IDR | With 🪙 icon |
| E-money revenue | `SummaryReport.emoney_revenue` | Formatted IDR | With 💳 icon |
| RFID revenue | `SummaryReport.rfid_revenue` | Formatted IDR | With 🏷️ icon |
| Active vehicles | `SummaryReport.active_transactions` | Number | Currently parked |
| Average fee | `SummaryReport.average_fee` | Formatted IDR | Small text |

**Update frequency**: Poll every 30s or refresh after each transaction completion.

### 3.6 Transaction Lookup & Detail

**Position**: Main content area, top

#### 3.6.1 Lookup Input

| Element | Behavior |
|---------|----------|
| Barcode input field | Already exists. Should auto-focus on page load and after transaction completion. |
| Auto-lookup on vehicle detected | When `vehicle_detected` WS event fires, auto-call `lookupTransaction()` if `card_number` is present in event data |
| Plate number input | Secondary input for manual plate entry |
| Lost ticket toggle | Checkbox/button that switches lookup to "no barcode" mode, requiring vehicle type selection instead |

#### 3.6.2 Transaction Detail Card

| Element | Data Source | Presentation |
|---------|------------|--------------|
| Barcode | `ParkingTransaction.barcode` | Large monospace font, copyable |
| Card number | `ParkingTransaction.card_number` | Small tag, colored by payment method |
| Plate number | `ParkingTransaction.plate_number` | Bold, large |
| Vehicle type | `VehicleType.name` | Icon + text (🛵 Motor, 🚗 Mobil, 🚐 Van, 🚌 Bus) |
| Entry time | `ParkingTransaction.entry_time` | Formatted: "Sel, 6 Mei 2025 14:30" |
| Duration | `now - entry_time` | **Live timer**, updating every minute: "2j 15m" |
| Gate-in | `gate_in.name` (via relationship) | "Masuk via GIN01" |
| Status | `ParkingTransaction.status` | Pulsing colored badge |
| Lost ticket | `ParkingTransaction.is_lost_ticket` | Red ⚠️ warning banner |
| Member info | `Member.name`, `valid_until` | "Member: PT Karya Utama (valid s/d 2025-12)" |
| Notes | `ParkingTransaction.notes` | Editable text area |

#### 3.6.3 Tariff Breakdown

| Element | Data Source | Presentation |
|---------|------------|--------------|
| Base tariff | `VehicleType.base_tariff` | "Tarif awal (1 jam): Rp 5.000" |
| Hourly rate | `VehicleType.hourly_rate` | "Rp 3.000/jam berikutnya" |
| Grace period | Config default 15 min | "Gratis 15 menit pertama" |
| Calculated hours | Computed from duration | "2 jam × Rp 3.000 = Rp 6.000" |
| Overnight charge | `VehicleType.overnight_tariff` | "Biaya overnight: Rp 10.000" (if applicable) |
| Daily cap | `VehicleType.max_daily_cap` | "Maksimal harian: Rp 50.000" |
| **Total fee** | `ParkingTransaction.fee` | **Large bold: Rp 11.000** |

#### 3.6.4 Entry & Exit Snapshots

The POS must show **both** the entry and exit camera snapshots side by side at the exit gate, matching the standard Indonesian parking POS pattern. The entry snapshot shows the vehicle when it entered, and the exit snapshot shows the vehicle when it arrived at the exit. This allows the operator to visually verify it's the same vehicle and compare the plate numbers.

**Layout**: Two images side by side in a single row

```
┌──────────────────────┬──────────────────────┐
│  📷 FOTO MASUK        │  📷 FOTO KELUAR      │
│                       │                       │
│  [Entry photo from    │  [Exit photo from     │
│   gate-in camera]     │   gate-out camera]   │
│                       │                       │
│  Plat: B 1234 AB      │  Plat: B 1234 AB      │
│  Akurasi: 92%         │  Akurasi: 87%         │
│  06 Mei 2025 14:30    │  06 Mei 2025 16:45    │
│  Masuk via: GIN01     │  Gerbang: GOUT01      │
└──────────────────────┴──────────────────────┘
```

**Entry Snapshot (left)**:

| Element | Data Source | Presentation |
|---------|------------|--------------|
| Entry photo | `Snapshot` where `snapshot_type="entry"` and `parking_transaction_id=currentTransaction.id` | Full-width image in left panel |
| Detected plate | `Snapshot.detected_plate` | Text overlay on image with confidence % |
| Accuracy | `Snapshot.confidence` | Percentage next to plate number |
| Timestamp | `Snapshot.created_at` | "06 Mei 2025 14:30" |
| Gate name | `Snapshot.gate_id` → Gate name | "Masuk via: GIN01" |

**Exit Snapshot (right)**:

| Element | Data Source | Presentation |
|---------|------------|--------------|
| Exit photo | `Snapshot` where `snapshot_type="exit"` and `parking_transaction_id=currentTransaction.id` | Full-width image in right panel |
| Detected plate | `Snapshot.detected_plate` | Text overlay on image with confidence % |
| Accuracy | `Snapshot.confidence` | Percentage next to plate number |
| Timestamp | `Snapshot.created_at` | "06 Mei 2025 16:45" |
| Gate name | `Snapshot.gate_id` → Gate name | "Gerbang: GOUT01" |

**Live exit photo**: The exit snapshot is captured by the ARQ worker when a `vehicle_detected` event fires at the exit gate. The frontend should:
1. Show a placeholder/loading state when the vehicle is detected but the snapshot hasn't arrived yet
2. Auto-fetch the exit snapshot via `GET /api/transactions/{id}/snapshots` once the transaction is looked up
3. Update in real-time if a new exit snapshot arrives

**Comparison highlights**: If both entry and exit plates are detected, highlight differences:
- Plates match → green check ✅ on the exit snapshot
- Plates differ → red warning ⚠️ on the exit snapshot, operator should verify

**API**: Fetch both snapshots with `GET /api/transactions/{id}/snapshots` (returns array with `entry` and `exit` snapshots). Currently there is no dedicated endpoint for this — it needs to be created (see Section 4).

### 3.7 Payment Panel

**Position**: Main content area, bottom-right

#### 3.7.1 Payment Method Buttons

| Button | Color | Keyboard | Enabled When |
|--------|-------|----------|-------------|
| 🪙 Bayar Tunai | Blue (primary) | F1 | `canPayCash` && transaction loaded |
| 🏷️ Bayar RFID | Green (success) | F2 | `canPayRfid` && transaction loaded |
| 💳 Bayar E-Money | Orange (warning) | F3 | `canPayEmoney` && transaction loaded |
| 🎫 Tiket Hilang | Red (danger) | F4 | Always (opens lost-ticket flow) |
| 🔓 Buka Palang | Teal (info) | F5 | `isWaitingPayment` or `isTimeout` (always accessible for admin) |

#### 3.7.2 Cash Payment Modal (Expanded)

| Element | Data Source | Type | Notes |
|---------|------------|------|-------|
| Total due | `ParkingTransaction.fee` | Large bold text | "TOTAL: Rp 11.000" |
| Quick denomination buttons | UI-only | Row of buttons | Rp 2K, 5K, 10K, 20K, 50K, 100K — adds to received amount |
| Amount received | `cashReceived` | Number input | Auto-filled with exact amount |
| Change | `cashReceived - fee` | Computed, readonly | Highlighted green if > 0 |
| Print receipt toggle | UI-only (default ON) | Checkbox | Suppress printing for re-print only |
| Confirm button | — | Button | Enter key submits |

#### 3.7.3 E-Money Payment Status (Expanded)

| State | Icon | Color | Text |
|-------|------|-------|------|
| WAITING_CARD | 💳 | Blue | "Tempelkan kartu e-money Anda..." |
| PROCESSING | ⏳ | Orange | "Memproses pembayaran..." |
| SUCCESS | ✅ | Green | "Pembayaran berhasil! Saldo: Rp {balance_after}" |
| LOST_CONTACT | ⚠️ | Yellow | "Kontak terputus. Tap ulang untuk koreksi." |
| WRONG_CARD | ❌ | Red | "Kartu tidak sesuai." |
| INSUFFICIENT | ❌ | Red | "Saldo tidak cukup. Saldo: Rp {balance}" |
| FAILED | ❌ | Red | "Transaksi gagal. Coba lagi." |

**Additional detail when card is detected:**

| Element | Data Source | Notes |
|---------|------------|-------|
| Card type | `card_type` from deduct_result or PASSTI event | eMoney, Brizzi, TapCash, Flazz badge |
| Card number (masked) | Last 4 digits of `card_number` | ••••4521 |
| Balance before | `balance_before` | Rp 50.000 |
| Amount deducted | `amount_deducted` | -Rp 11.000 |
| Balance after | `balance_after` | Rp 39.000 |

**Action buttons on failure states:**
- LOST_CONTACT → "Tap Ulang" (retry), "Bayar Tunai", "Bayar RFID"
- INSUFFICIENT → "Bayar Tunai", "Bayar RFID"
- WRONG_CARD → "Tap Ulang"
- FAILED → "Coba Lagi", "Bayar Tunai"

These buttons must actually trigger the corresponding payment flows (currently non-functional stubs).

#### 3.7.4 RFID Payment Modal (Expanded)

When an RFID card is scanned or entered:

| Element | Data Source | Notes |
|---------|------------|-------|
| Card number | Input or auto-populated from WS event | Auto-filled if `rfid_card_read` event received |
| Member name | `Member.name` (auto-lookup) | "Ahmad Fauzi" |
| Member group | `MemberGroup.name` | "Karyawan" |
| Validity | `Member.valid_from` → `valid_until` | "Valid: 01 Jan 2025 - 31 Dec 2025" |
| Status | `Member.is_active` + date check | Green badge or red "EXPIRED" |
| Vehicle info | `Member.plate_number` + `VehicleType.name` | "B 1234 AB — Mobil" |
| Last entry | `Member.last_entry_at` | "Terakhir masuk: 2 Mei 2025 08:15" |

#### 3.7.5 Lost Ticket Flow

**Trigger**: Button "Tiket Hilang" (F4) or manual selection

| Step | Action | Notes |
|------|--------|-------|
| 1 | Select vehicle type | Dropdown from `VehicleType` list |
| 2 | Calculate penalty | `VehicleType.lost_ticket_penalty` — flat fee |
| 3 | Optionally enter plate number | Manual input |
| 4 | Show penalty total | "Denda tiket hilang: Rp {penalty}" |
| 5 | Choose payment method | Cash / e-money (same flow as normal) |
| 6 | Create transaction with `is_lost_ticket=True` | API call to `POST /api/payments/cash` with `is_lost_ticket=True` |

**Note**: Backend `lookup` endpoint may need a new parameter to handle lost-ticket mode (no barcode, create transaction with penalty fee). Currently the `fee` calculation in `transaction.py` checks `is_lost_ticket` and applies `VehicleType.lost_ticket_penalty`.

### 3.8 Recent Transactions Mini-List

**Position**: Bottom bar, scrollable horizontally

| Element | Data Source | Type | Notes |
|---------|------------|------|-------|
| Last 10 transactions | `GET /api/transactions?limit=10&sort=-exit_time&gate_out_id={id}` | Scrollable list | Auto-refresh on transaction completion |
| Per row: time, plate, type, method, amount | Transaction fields | Compact card | Color-coded payment method badge |

### 3.9 Alerts Panel

**Position**: Overlay or top-right notification

| Alert Type | Source | Behavior |
|-----------|--------|-----------|
| Payment timeout | WS `timeout_alert` event | Already shown. Add countdown timer with seconds. |
| Sensor stuck | WS `reader_error` or `OperatorAlert` SENSOR_STUCK | Red banner, acknowledge button |
| E-money reader offline | WS `heartbeat.passti_ok = false` | Yellow warning in gate status panel |
| Controller offline | WS `heartbeat.controller_ok = false` | Red warning, gate operations disabled |
| Unresolved alerts | `GET /api/audit-logs?is_resolved=false` | Badge count in header |
| Abandoned vehicle | WS `vehicle_left` with reason="abandoned" | Notification toast |

### 3.10 Shift Handover

**Position**: Accessible from header (Shift dropdown)

| Element | Data Source | Notes |
|---------|------------|-------|
| Current shift name + time | `Shift` model | "Pagi (06:00 - 14:00)" |
| Shift summary | `GET /api/reports/shift?shift_id={id}` | Total transactions, revenue breakdown |
| Print shift report button | New endpoint or report | For thermal printer |

---

## 4. New/Modified API Endpoints Needed

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `GET /api/areas` | GET | List parking areas with occupancy | ✅ Exists |
| `GET /api/site-config` | GET | Site name, logo, settings | ✅ Exists |
| `GET /api/reports/summary` | GET | Daily summary for POS dashboard | ✅ Exists |
| `GET /api/transactions?limit=10` | GET | Recent transactions for mini-list | ✅ Exists |
| `GET /api/transactions/{id}/snapshots` | GET | Get entry + exit snapshots for a transaction | ❌ New endpoint needed |
| `GET /api/reports/shift?shift_id={id}` | GET | Current shift summary | ✅ Exists |
| `POST /api/payments/lookup` | GET | Add `is_lost_ticket` param | ⚠️ Needs modification |
| `POST /api/payments/cash` | POST | Add `is_lost_ticket` param | ⚠️ Needs modification |
| `POST /api/payments/reprint` | POST | Reprint last receipt | ❌ New endpoint needed |
| `GET /api/gates/{id}/status` | GET | Full gate status (state, sensors, peripherals) | ❌ New endpoint needed (or use WS heartbeat) |
| `WS event: shift_summary` | Push | Push shift summary updates | ❌ Optional, can poll |
| `WS event: area_occupancy` | Push | Push occupancy changes | ❌ Optional, can poll |

---

## 5. Frontend Component Structure

```
pages/index.vue (POS page)
├── components/pos/
│   ├── PosHeader.vue              # 3.1 - Site, shift, operator, clock, alerts
│   ├── ParkingAreaStatus.vue      # 3.2 - Area name, capacity, occupancy bar
│   ├── GateStatusPanel.vue        # 3.3 - Gate state, sensors, devices, controls
│   ├── QuickActions.vue           # 3.4 - Manual open, reprint, display, audio
│   ├── DailySummary.vue           # 3.5 - Today's stats
│   ├── TransactionLookup.vue      # 3.6.1 - Barcode/plate input, lost-ticket toggle
│   ├── TransactionDetail.vue      # 3.6.2 - All transaction info displayed
│   ├── TariffBreakdown.vue        # 3.6.3 - Fee calculation detail
│   ├── DualSnapshots.vue          # 3.6.4 - Entry & exit photos side by side
│   ├── PaymentPanel.vue           # 3.7 - All payment buttons + state display
│   ├── CashPaymentModal.vue       # 3.7.2 - Cash with denominations
│   ├── EmoneyStatusPanel.vue      # 3.7.3 - E-money payment progress + details
│   ├── RfidPaymentModal.vue       # 3.7.4 - RFID with member info
│   ├── LostTicketModal.vue        # 3.7.5 - Lost ticket flow
│   ├── RecentTransactions.vue     # 3.8 - Bottom mini-list
│   ├── AlertBanner.vue            # 3.9 - Timeout, sensor, hardware alerts
│   └── ShiftHandover.vue          # 3.10 - Shift info + summary
```

---

## 6. Store Updates Required

### `gate.js` — Additions

| State/Action | Type | Description |
|-------------|------|-------------|
| `gateState` | State | Current daemon state (IDLE, VEHICLE_PRESENT, etc.) from heartbeat |
| `sensorStates` | State | IN1/IN2/IN3/IN4 sensor status from heartbeat |
| `controllerOk` | State | Controller connection status |
| `readerOk` | State | E-money reader status |
| `isLostTicket` | State | Whether current flow is lost-ticket mode |
| `currentShift` | State | Active shift info |
| `dailySummary` | State | Today's revenue/transaction summary |
| `recentTransactions` | State | Last 10 transactions |
| `unresolvedAlerts` | State | Count of unresolved alerts |
| `entrySnapshot` | State | Entry snapshot URL for current transaction |
| `exitSnapshot` | State | Exit snapshot URL for current transaction |
| `memberInfo` | State | Member details when RFID card detected |
| `areaInfo` | State | Parking area capacity/occupancy |
| `fetchDailySummary()` | Action | `GET /api/reports/summary` |
| `fetchRecentTransactions()` | Action | `GET /api/transactions?limit=10` |
| `fetchAreaInfo()` | Action | `GET /api/areas` |
| `fetchSnapshots()` | Action | `GET /api/transactions/{id}/snapshots` (returns both entry & exit) | |
| `lookupMember()` | Action | Lookup member by card number |
| `manualOpenGate()` | Action | `POST /api/gates/{id}/open` with reason |
| `reprintReceipt()` | Action | `POST /api/payments/reprint` |

### `website.js` — Additions

| State/Action | Type | Description |
|-------------|------|-------------|
| `siteConfig` | State | Site name, logo, settings from `/api/site-config` |
| `fetchVehicleTypes()` | Action | Already exists but not called in `loadAll()` |
| `fetchSiteConfig()` | Action | Load site configuration |

---

## 7. Keyboard Shortcuts (Complete)

| Key | Action | Context |
|-----|--------|---------|
| F1 | Open cash payment modal | Transaction loaded |
| F2 | Open RFID payment modal | Transaction loaded |
| F3 | Start e-money payment | Transaction loaded |
| F4 | Open lost ticket modal | Always |
| F5 | Manual gate open | Always (admin) or waiting payment |
| F6 | Reprint last receipt | Transaction completed |
| Space | Open gate (after cash payment) | `awaitingGateOpen === true` |
| Escape | Close any open modal | Always |
| Tab | Focus barcode input | Always |
| Enter | Confirm current modal action | Inside modal |

---

## 8. Special Flows

### 8.1 Auto-Lookup on Vehicle Detection

```
WS: vehicle_detected →
  If event.card_number exists:
    lookupTransaction({ cardNumber: event.card_number })
  Else:
    Flash "Kendaraan terdeteksi" banner
    Focus barcode input
    Auto-start waiting timer
```

### 8.2 Lost Ticket Flow

```
User presses F4 →
  LostTicketModal opens →
  Select vehicle type (from websiteStore.vehicleTypes) →
  Show penalty: VehicleType.lost_ticket_penalty →
  Optionally enter plate number →
  Choose payment method →
  POST /api/payments/cash { is_lost_ticket: true, vehicle_type_id, plate_number } →
  Transaction created with penalty fee →
  Normal payment flow continues
```

### 8.3 E-Money Recovery Flow

```
LOST_CONTACT state →
  "Tap Ulang" button → retries deduct with same card
  "Bayar Tunai" button → switches to cash flow with same transaction
  "Bayar RFID" button → opens RFID modal with same transaction
INSUFFICIENT state →
  "Bayar Tunai" button → cash payment for remaining amount
  "Bayar RFID" button → RFID payment for remaining amount
```

### 8.4 Snapshot Comparison Flow

```
Vehicle detected at exit gate →
  WS: vehicle_detected event fires →
    ARQ worker captures exit snapshot →
    POS shows exit photo placeholder/loading →

Transaction looked up (barcode/card) →
  Fetch entry snapshot via GET /api/transactions/{id}/snapshots →
  Display entry photo (left) and exit photo (right) side by side →

  If both plates detected:
    Entry plate = exit plate → ✅ green check, auto-match
    Entry plate ≠ exit plate → ⚠️ red warning, operator must verify manually
```

### 8.5 Shift Handover Flow

```
Header: Click shift badge →
  ShiftHandover panel opens →
  Shows current shift summary (transactions, revenue) →
  Operator can print shift report →
  Admin can end shift (requires admin role)
```

---

## 9. Responsive Design Notes

The POS must work on these screen sizes:

| Size | Resolution | Layout |
|------|-----------|--------|
| Touchscreen POS | 1366×768 or 1920×1080 | Full layout, 3 columns |
| Tablet | 1024×768 | 2 columns: sidebar collapses to icons |
| Mobile (rare) | Any width | Single column, tabbed interface |

For the primary POS touchscreen:
- Minimum touch target: 44×44px (WCAG)
- Large fonts for fees: 24px+ for amounts
- High contrast colors for status indicators
- No hover-only interactions

---

## 10. Color Scheme & Visual Language

| Element | Color | Hex |
|---------|-------|-----|
| Cash payment | Blue | `#409EFF` |
| RFID payment | Green | `#67C23A` |
| E-money payment | Orange | `#E6A23C` |
| Lost ticket | Red | `#F56C6C` |
| Manual gate open | Teal | `#00BFA5` |
| Active/IDLE state | Gray | `#909399` |
| Vehicle present | Orange | `#E6A23C` |
| Waiting payment | Gold | `#F5DA44` |
| Transaction success | Green | `#67C23A` |
| Timeout/error | Red | `#F56C6C` |
| Occupancy safe | Green | `#67C23A` |
| Occupancy warning | Yellow | `#E6A23C` |
| Occupancy full | Red | `#F56C6C` |
| Gate online | Green | `#67C23A` |
| Gate offline | Red | `#F56C6C` |

---

## 11. Implementation Priority

### Phase 1 — Core POS Redesign (Must Have)

| # | Task | Component |
|---|------|-----------|
| 1 | Redesign page layout to 3-column (sidebar + main) | `pages/index.vue` |
| 2 | Add header bar with shift, operator, clock, alerts | `PosHeader.vue` |
| 3 | Add parking area status panel | `ParkingAreaStatus.vue` |
| 4 | Expand transaction detail with tariff breakdown | `TransactionDetail.vue` + `TariffBreakdown.vue` |
| 5 | Add quick denomination buttons to cash modal | `CashPaymentModal.vue` |
| 6 | Add vehicle type icons | `TransactionDetail.vue` |
| 7 | Add live duration timer | `TransactionDetail.vue` |
| 8 | Add dual snapshots (entry + exit) with plate comparison | `DualSnapshots.vue` |
| 9 | Add e-money detail (card type, balance before/after) | `EmoneyStatusPanel.vue` |
| 10 | Add lost ticket flow | `LostTicketModal.vue` |
| 11 | Add manual gate open (always accessible) | `QuickActions.vue` |
| 12 | Add keyboard shortcuts F4, F5, F6 | `pages/index.vue` |

### Phase 2 — Dashboard & Monitoring (Should Have)

| # | Task | Component |
|---|------|-----------|
| 13 | Add gate status panel (state, sensors, devices) | `GateStatusPanel.vue` |
| 14 | Add daily summary panel | `DailySummary.vue` |
| 15 | Add recent transactions mini-list | `RecentTransactions.vue` |
| 16 | Add alert banner for hardware/sensor issues | `AlertBanner.vue` |
| 17 | Add auto-lookup on vehicle_detected WS event | `TransactionLookup.vue` |
| 18 | Add RFID member info display | `RfidPaymentModal.vue` |

### Phase 3 — Polish & Advanced (Nice To Have)

| # | Task | Component |
|---|------|-----------|
| 19 | Add shift handover panel | `ShiftHandover.vue` |
| 20 | Add receipt reprint button | `QuickActions.vue` |
| 21 | Add display text custom input | `QuickActions.vue` |
| 22 | Add play audio controls | `QuickActions.vue` |
| 23 | Implement e-money recovery flow (actual pay cash/RFID buttons) | `EmoneyStatusPanel.vue` |
| 24 | Add shift summary print | `ShiftHandover.vue` |
| 25 | Add print receipt toggle in cash modal | `CashPaymentModal.vue` |
| 26 | Add plate number correction input | `TransactionDetail.vue` |

---

*Last updated: May 7, 2026 — Added dual snapshot (entry + exit) section*