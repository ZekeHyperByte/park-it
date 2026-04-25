# E-Parking System v2 — Development Plan

> **Stack:** FastAPI + SQLAlchemy async + Nuxt 3 + PostgreSQL + Redis  
> **Timeline:** 12 Weeks  
> **Last Updated:** 25 April 2026

---

## Architecture Summary

```
Nuxt 3 SPA (Element Plus + Pinia + Vue Router)
     │ HTTP/REST (JWT httpOnly cookie)     │ WebSocket /ws/
     ▼                                     ▼
FastAPI Backend (Gunicorn + Uvicorn workers)
  SQLAlchemy async │ Alembic │ Pydantic │ ARQ │ structlog
     │
     ├── Redis Streams  parking.commands.{gate_id}   → Daemon (ACK-based, persistent)
     └── Redis Pub/Sub  parking.events.{gate_id}     ← Daemon (fire-and-forget)
                                     │
                          Python Hardware Daemons
                          gate_in.py │ gate_out.py
                          (one per gate — TCP controller + Serial PASSTI)
                                     │
                          protocols/ (stdlib only)
                          compass │ enet │ passti │ escpos │ frame
                                     │
                          Physical Hardware
                          Gate Controllers │ PASSTI E-Money │ Printers │ Cameras
```

---

## Repository Structure

```
parking-system-v2/
├── api/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── models/          ← SQLAlchemy models (imported by workers/)
│   │   ├── schemas/         ← Pydantic request/response
│   │   ├── services/        ← Business logic (tariff, member, settlement)
│   │   ├── websocket/       ← WS handlers + Redis broadcaster
│   │   ├── middleware/       ← Auth, CORS, logging
│   │   └── cache/           ← Redis cache helpers
│   ├── alembic/
│   ├── database.py          ← api/ ONLY — daemons never import this
│   └── tests/
│
├── frontend/
│   ├── pages/               ← login, index(POS), gate-in, transaksi,
│   │                           setting, device, member, report, notification
│   ├── components/
│   ├── stores/              ← auth.js, website.js, gate.js
│   ├── composables/         ← useApi.js, useCrud.js
│   └── plugins/             ← websocket.js (auto-reconnect)
│
├── daemons/
│   ├── gate_in.py
│   ├── gate_out.py
│   └── base.py              ← Shared: Redis Streams consumer, heartbeat
│
├── protocols/               ← stdlib ONLY — zero external deps
│   ├── compass/
│   ├── enet/
│   ├── passti/
│   ├── escpos/
│   └── frame.py
│
├── workers/
│   ├── critical/            ← print_ticket, print_receipt, take_snapshot
│   ├── background/          ← settlement, cleanup, notification
│   └── settings.py          ← CriticalWorkerSettings + BackgroundWorkerSettings
│
├── shared/
│   ├── config.py            ← pydantic-settings
│   ├── redis.py             ← Redis client, Streams + Pub/Sub helpers
│   ├── events.py            ← All Redis message schemas (Pydantic)
│   └── logging.py           ← structlog config + trace_id binding
│
├── docker/
├── scripts/
└── pyproject.toml
```

### Dependency Contract

| Layer | Can Import | Cannot Import |
|---|---|---|
| `protocols/` | stdlib only | everything else |
| `shared/` | protocols/, pydantic, redis | api/, workers/, daemons/ |
| `api/` | shared/, sqlalchemy, fastapi | daemons/ |
| `workers/` | api/models/, shared/ | daemons/ |
| `daemons/` | protocols/, shared/events.py | api/, workers/, database.py |

---

## Data Models

### New Models

| Model | Purpose |
|---|---|
| `EmoneyTransaction` | PASSTI deduct records — card, amount, balance, raw hex, settlement link |
| `EmoneySettlement` | Settlement file tracking — filename, batch, upload status, bank response |
| `EmoneyReader` | PASSTI reader config — serial port, baudrate, encrypted init key, MID/TID |
| `ShiftEmoneySnapshot` | Per-shift, per-card-type count + total amount |
| `AbandonedVehicleLog` | Gate-out timeout log — snapshot, waiting time, resolution type |

### Modified Models

| Model | Changes |
|---|---|
| `ParkingTransaction` | + `payment_method: Enum(CASH, RFID_MEMBER, EMONEY, PENDING)`, `member_id FK`, `emoney_transaction_id FK` |
| `GateIn` | + `gate_mode: Enum(CASH, RFID, EMONEY)`, `emoney_minimum_balance`, `print_decision_timeout_seconds`, `has_close_sensor`, `gate_close_duration_ms` |
| `GateOut` | + `emoney_reader_id FK`, `payment_timeout_seconds (default 120)`, `has_close_sensor`, `gate_close_duration_ms` |
| `Setting` | + `emoney_minimum_balance_default`, `payment_timeout_seconds_default`, `settlement_schedule`, `settlement_auto_upload` |

### Key Constraints

```sql
-- Prevent duplicate active card
CREATE UNIQUE INDEX uq_active_card
ON parking_transactions(card_number)
WHERE card_number IS NOT NULL AND status = 'active';

-- Fast settlement query
CREATE INDEX idx_unsettled_emoney ON emoney_transactions(created_at)
WHERE settlement_batch_id IS NULL AND status = 'SUCCESS';

-- Fast correction query
CREATE INDEX idx_pending_correction ON emoney_transactions(created_at)
WHERE status IN ('LOST_CONTACT', 'CORRECTION_FAILED');

-- Atomic capacity fix (resolves v1 bug)
UPDATE area_parkir SET current = current + 1
WHERE id = :id AND current < capacity
RETURNING current;
-- 0 rows returned = parking full. Can never go negative.
```

---

## Gate-In State Machine

### All Methods — Shared Entry

```
IDLE
  └─ IN1 ON (vehicle detected)
VEHICLE_PRESENT
  └─ Send close_gate to controller
     Wait: has_close_sensor → IN3 confirm | fallback → gate_close_duration_ms timer
GATE_CLOSED
  └─ ARQ critical: take_snapshot(type='entry')
     Branch to method flow ↓
```

### Cash Mode

```
WAITING_BUTTON
  └─ IN2 ON (ticket button pressed)
PROCESSING
  └─ Create ParkingTransaction (barcode CODE39, card_number=NULL)
     ARQ critical: print_ticket
     play_audio: track 2 (Silakan Ambil Tiket)
     Publish open_gate → Redis Stream
OPENING → vehicle passes (IN3) → IDLE
```

### RFID Member Mode

```
WAITING_CARD
  └─ Wiegand card read (W/X from controller)
VALIDATING
  └─ FastAPI: check Redis cache → fallback PostgreSQL
     ├─ Valid member
     │    Create ParkingTransaction (card_number, member_id, RFID_MEMBER)
     │    play_audio: track 7 (Selamat Datang)
     │    Publish open_gate → Redis Stream → OPENING → IDLE
     └─ Invalid/Expired
          play_audio: track 3/4 → display error → IDLE
```

### E-Money Mode

```
WAITING_CARD
  └─ PASSTI card tap
CHECKING_BALANCE
  └─ CheckBalance command to reader
     ├─ Balance < emoney_minimum_balance
     │    display "Saldo Tidak Cukup" → play audio → IDLE
     └─ Balance ≥ threshold
WAITING_PRINT_DECISION
  └─ display "Cetak Tiket? Tekan Tombol"
     Start print_decision_timeout_seconds timer (default 10s)
     ├─ IN2 pressed → ARQ: print_ticket
     └─ Timeout → no ticket
PROCESSING
  └─ Create ParkingTransaction (card_number, PENDING)
     play_audio: track 7
     Publish open_gate → Redis Stream
OPENING → vehicle passes → IDLE
```

---

## Gate-Out State Machine

### Shared Exit Sequence

```
IDLE
  └─ IN1 ON (vehicle at exit)
VEHICLE_PRESENT
  └─ 500ms debounce
     ARQ critical: take_snapshot(type='exit')
     WebSocket: notify POS
     Start payment_timeout_seconds countdown (default 120s)
WAITING_PAYMENT
  └─ Three concurrent asyncio tasks (FIRST_COMPLETED wins, others cancelled):
     ├─ Task 1: wait_for_wiegand()      → RFID flow
     ├─ Task 2: wait_for_passti_tap()   → E-money flow
     ├─ Task 3: wait_for_pos_confirm()  → Cash flow (Redis Stream from FastAPI)
     └─ Timeout elapsed
TIMEOUT_ALERT
  └─ Publish timeout_alert event
     display "Mohon Hubungi Petugas"
     play_audio: track 8
     WebSocket: push alert to POS (snapshot + elapsed time + action buttons)
     ├─ IN1 OFF (vehicle left) → log AbandonedVehicleLog (VEHICLE_LEFT) → IDLE
     ├─ Operator: Buka Manual  → ManualOpenLog + AbandonedVehicleLog (MANUAL_OPEN)
     │                           Publish open_gate → IDLE
     └─ Operator: Reset Gate   → AbandonedVehicleLog (OPERATOR_RESET) → IDLE
```

### Cash Exit

```
Task 3 wins (POS confirms payment):
  └─ Operator scans barcode / enters plate
     FastAPI finds transaction, calculates tariff
     Operator confirms cash received
     FastAPI publishes cash_payment_confirmed → Redis Stream (resolves Task 3)
     FastAPI publishes open_gate → Redis Stream
     ARQ critical: print_receipt
OPENING → vehicle passes → IDLE
```

### RFID Exit

```
Task 1 wins (Wiegand read):
  └─ FastAPI finds transaction: card_number WHERE status='active'
     Validates member still active (Redis cache)
     No fee. No POS interaction.
     Update ParkingTransaction (RFID_MEMBER, paid, completed)
     Publish open_gate → Redis Stream
     play_audio: track 9 (Terima Kasih)
OPENING → vehicle passes → IDLE
```

### E-Money Exit

```
Task 2 wins (PASSTI tap):
  └─ FastAPI finds transaction: card_number WHERE status='active'
     Calculates tariff
     → E-Money Deduct Flow (see below)
     On SUCCESS: update ParkingTransaction, open gate, print receipt
OPENING → vehicle passes → IDLE
```

---

## E-Money Deduct Flow

Daemon handles all hardware complexity internally. Only final result published to FastAPI.

| `deduct_result` status | FastAPI action |
|---|---|
| `SUCCESS` | Create EmoneyTransaction, update ParkingTransaction, open gate, print receipt |
| `LOST_CONTACT` | Create EmoneyTransaction (LOST_CONTACT), show "Proses Koreksi" on POS — await final |
| `SUCCESS` (after LC) | Update EmoneyTransaction to SUCCESS, open gate |
| `CORRECTION_FAILED` | Update EmoneyTransaction, operator intervention |
| `WRONG_CARD` | Display "Gunakan Kartu Sebelumnya" — reader enforces same card |
| `INSUFFICIENT_BALANCE` | Display balance + offer cash/RFID alternative |
| `TIMEOUT` | Daemon runs GetLastTransaction, verifies card_number + deduct_amount + transaction_counter |
| `FAILED` | Create EmoneyTransaction (FAILED), operator intervention |

> **TIMEOUT rule:** All three fields must match. Any mismatch = FAILED. Prevents treating previous customer's transaction as current.

> **DEDUCT_INTERVAL (01 10 07):** Daemon handles internally with asyncio.sleep(2) + retry. Never exposed to FastAPI.

---

## Lost Contact State Machine

| From | Trigger | To | Action |
|---|---|---|---|
| NORMAL | 01 10 05 | LOST_CONTACT | Persist state to Redis. Publish event. Create EmoneyTransaction. |
| LOST_CONTACT | Same card | AUTO_CORRECTION | Reader auto-continues deduct |
| LOST_CONTACT | Different card | CORRECTION_FAILED | 01 10 06 returned |
| AUTO_CORRECTION | Success | NORMAL | Complete transaction, open gate |
| AUTO_CORRECTION | Fail | CORRECTION_FAILED | Operator intervention |
| CORRECTION_FAILED | EF 01 04 | NORMAL | Reset reader, MANUAL_OVERRIDE recorded |
| CORRECTION_FAILED | Manual resolve | NORMAL | correction_note recorded |

---

## Redis Event Schema

### Daemon → FastAPI — `parking.events.{gate_id}` (Pub/Sub)

| Event | Key Payload |
|---|---|
| `vehicle_detected` | gate_id, sensor, timestamp |
| `gate_closed` | gate_id, timestamp |
| `rfid_card_read` | gate_id, card_number, channel (W/X), timestamp |
| `passti_card_tap` | gate_id, card_number, card_type, timestamp |
| `ticket_button_pressed` | gate_id, timestamp |
| `vehicle_passed` | gate_id, timestamp |
| `gate_opened` | gate_id, timestamp |
| `deduct_result` | gate_id, status, card_number, card_type, deduct_amount, balance_before, balance_after, transaction_counter, raw_response_hex, timestamp |
| `cancel_correction_result` | gate_id, card_number, card_type |
| `timeout_alert` | gate_id, transaction_id (nullable), waiting_seconds, timestamp |
| `vehicle_left` | gate_id, reason (passed/abandoned), timestamp |
| `reader_error` | gate_id, error_code, message, timestamp |
| `heartbeat` | gate_id, controller_ok, passti_ok, timestamp (every 30s) |

### FastAPI → Daemon — `parking.commands.{gate_id}` (Redis Streams — ACK required)

| Command | Key Payload |
|---|---|
| `open_gate` | gate_id, duration_seconds |
| `close_gate` | gate_id |
| `play_audio` | gate_id, track |
| `display_text` | gate_id, line1, line2, brightness, mode |
| `buzzer` | gate_id, success: bool |
| `print_ticket` | gate_id, barcode, gate_name, timestamp, barcode_format: CODE39 |
| `print_receipt` | gate_id, transaction data |
| `check_balance` | gate_id, minimum_threshold |
| `deduct` | gate_id, amount, timeout_seconds, expected_card_number, expected_transaction_counter |
| `cancel_correction` | gate_id |
| `cash_payment_confirmed` | gate_id, transaction_id |
| `reset_gate` | gate_id, reason |

---

## Tech Optimization — Priority Order

| Priority | Optimization | Effort | Impact | Type |
|---|---|---|---|---|
| 1 | **Redis Streams for commands** — ACK-based, survives daemon restart | Low | Critical | Reliability |
| 2 | **structlog + trace_id** — correlate all logs per transaction | Low | Critical | Operability |
| 3 | **PostgreSQL partial indexes + SKIP LOCKED** — free perf + capacity bug fix | Low | High | Performance |
| 4 | **ARQ priority queues** — critical tier (print) never delayed by background (settlement) | Low | High | Reliability |
| 5 | **Redis cache** — member, tariff, gate config (5min TTL, explicit invalidation) | Medium | Medium | Performance |
| 6 | **Gunicorn + Redis WS broadcaster** — multi-worker WebSocket delivery | Medium | High | Reliability |
| 7 | **Daemon state persistence** — Redis-backed state recovery on restart | Medium | High | Reliability |

> **Rule:** Implement 1 and 2 before writing any other code. They affect every layer and are nearly impossible to retrofit.

---

## Frontend Pages

| Route | Page | Role | Key Features |
|---|---|---|---|
| `/login` | login.vue | All | httpOnly cookie auth |
| `/` | index.vue | Operator | POS — triple-method payment, timeout alert, snapshot display, keyboard shortcuts |
| `/gate-in` | gate-in.vue | Operator | Live gate status grid per gate |
| `/transaksi` | transaksi.vue | Operator/Admin | Transaction CRUD, ManualOpenLog, AbandonedVehicleLog |
| `/setting` | setting.vue | Admin | General, Vehicle Types, Users, Shifts, Areas, Backup |
| `/device` | device.vue | Admin | Cameras, Printers, POS, Gates, E-Money Readers |
| `/member` | member.vue | Operator/Admin | Members, Groups, Renewals, Reports |
| `/report` | report.vue | Admin | Date-range reports + e-money breakdown |
| `/notification` | notification.vue | Admin | Snapshots, Attendance, Logs, Settlement, Unresolved Transactions |

### Pinia Stores

- **`stores/auth.js`** — user, role (token managed by cookie)
- **`stores/website.js`** — reference data (gates, tariffs, members, readers)
- **`stores/gate.js`** — currentTransaction, paymentState, emoneyPaymentState, wsConnected, cameraSnapshot, waitingSeconds

### EmoneyPayment.vue States

| State | Display | Actions |
|---|---|---|
| WAITING_CARD | "Tempelkan kartu e-money" | Cancel |
| PROCESSING | Spinner | — |
| LOST_CONTACT | "Proses koreksi..." + spinner | Cancel Correction |
| WRONG_CARD | "Gunakan kartu sebelumnya" | Cancel |
| INSUFFICIENT | "Saldo tidak cukup: Rp X" | Bayar Tunai, Bayar RFID |
| SUCCESS | "Pembayaran berhasil: Rp X" | Auto-closes |
| FAILED | "Transaksi gagal" | Retry, Override |

---

## Deployment

### systemd Services

| Service | User | Command |
|---|---|---|
| `parking-api` | parking | `gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.app.main:app` |
| `parking-worker-critical` | parking | `arq workers.CriticalWorkerSettings` |
| `parking-worker-bg` | parking | `arq workers.BackgroundWorkerSettings` |
| `parking-daemon-gate-in-{id}` | parking | `python -m daemons.gate_in --gate-id {id}` |
| `parking-daemon-gate-out-{id}` | parking | `python -m daemons.gate_out --gate-id {id}` |

> `sudo usermod -aG dialout parking` — serial access without root. Never run daemons as root.

### Nginx — Critical Settings

```nginx
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;    # REQUIRED — default 60s drops idle connections
    proxy_send_timeout 3600s;
}
```

### Key Dependencies

```toml
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
gunicorn>=23.0.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.30.0
alembic>=1.14.0
pydantic>=2.9.0
pydantic-settings>=2.6.0
PyJWT[crypto]>=2.9.0          # NOT python-jose
passlib[bcrypt]>=1.7.4
arq>=0.26.0
redis>=5.2.0
pyserial>=3.5
python-escpos>=3.0
cryptography>=43.0.0
httpx>=0.27.0
structlog>=24.0.0
```

---

## Open Items

| Item | Question | Impact |
|---|---|---|
| UHF long-range readers | Still in use in v2, or replaced by PASSTI? | Separate daemon + protocol needed if yes |
| RTSP streaming | Is live camera stream-to-canvas needed? | rtsp-relay sidecar needed |
| Telegram notifications | Does client use Telegram gate alerts from v1? | ARQ background job if yes |
| Audio track numbers | Confirm tracks for "Saldo Tidak Cukup" and "Gunakan Kartu Sebelumnya" | play_audio payload |
| Controller type per gate | Document 1-relay vs 2-relay per gate in config | Protocol layer only, no business logic change |

---

## Locked Decisions

| Decision | Choice |
|---|---|
| Gate command IPC | Redis Streams (ACK-based) — not pub/sub |
| Gate event IPC | Redis Pub/Sub per-gate channel |
| Gate-in methods | Cash, RFID member, E-money — configured per gate |
| Gate-out method | All three simultaneous — asyncio.wait FIRST_COMPLETED |
| Camera timing (gate-in) | After gate finishes closing |
| Camera timing (gate-out) | IN1 ON + 500ms debounce |
| Payment timeout | Alert operator, gate stays closed, operator resolves |
| E-money gate-in | Balance check → driver chooses ticket print (10s timeout) |
| TIMEOUT verification | card_number + deduct_amount + transaction_counter — all three must match |
| LOST_CONTACT events | Intermediate signal published, then final SUCCESS or CORRECTION_FAILED |
| Shift assignment | gate_out_time — never gate_in_time |
| Capacity tracking | PostgreSQL SKIP LOCKED — fixes v1 negative capacity bug |
| Daemon state | Persisted to Redis on every transition — recovered on restart |
| Auth | JWT httpOnly cookies — never localStorage |
| Daemon user | parking + dialout group — never root |
| Logging | structlog + trace_id per transaction |
| WebSocket | Gunicorn multi-worker + Redis broadcaster |
| JWT library | PyJWT[crypto] — not python-jose |
| Docker networking | Bridge (not host) for daemons |
| Nginx WS timeout | 3600s |
