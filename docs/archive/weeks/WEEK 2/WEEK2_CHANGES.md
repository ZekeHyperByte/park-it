# Week 2 — Changes & Build Log

> **Date:** 25 April 2026
> **Scope:** Authentication, Core API, Protocol Foundations, Worker Infrastructure
> **Depends on:** Week 1 (Foundation & Database)

---

## Open Items Resolution

| # | Item | Decision |
|---|------|----------|
| 1 | **UHF long-range readers** | Still in use. Supported via W/X Wiegand parsing (X channel = UHF). |
| 2 | **RTSP streaming** | Focus on snapshots. Architecture keeps streaming door open via `camera_url`. No live canvas in Week 2. |
| 3 | **Telegram notifications** | Yes. Implemented as ARQ background job for gate timeout/hardware failure alerts. |
| 4 | **Audio track numbers** | User generates all voice files. See Audio Assets section below. |
| 5 | **Controller type per gate** | Configurable per gate. `relay_mode: Enum("SINGLE", "DUAL")`. |

---

## What Was Built

### 1. Authentication Layer

| File | Purpose |
|------|---------|
| `api/app/utils/password.py` | Bcrypt direct hashing (bypasses passlib v4 issues) |
| `api/app/utils/jwt.py` | PyJWT dual token: access (30min) + refresh (7d) |
| `api/app/services/auth.py` | authenticate_user, create_tokens, refresh, revoke |
| `api/app/middleware/auth.py` | JWT cookie extraction, user injection, role check |
| `api/app/routes/auth.py` | Login, logout, refresh, me |

**Key decisions:**
- `bcrypt` direct usage (not passlib) due to compatibility issues with bcrypt >= 4.0
- Dual JWT tokens: short-lived access token + long-lived refresh token, both in httpOnly cookies
- Token revocation via Redis denylist (avoids DB round-trip on every request)
- `request.state.current_user` injected by middleware for downstream route access

### 2. Pydantic Schemas

| File | Schemas |
|------|---------|
| `api/app/schemas/auth.py` | LoginRequest, TokenResponse, RefreshRequest |
| `api/app/schemas/user.py` | UserCreate, UserUpdate, UserResponse, UserListResponse |
| `api/app/schemas/gate.py` | GateIn/GateOut CRUD schemas |
| `api/app/schemas/setting.py` | SettingCreate, SettingUpdate, SettingResponse |
| `api/app/schemas/common.py` | PaginatedResponse, ErrorResponse, SuccessResponse |

### 3. Core CRUD Routes

| Route | File | Methods | Access |
|-------|------|---------|--------|
| `/api/users` | `api/app/routes/users.py` | GET, POST, PATCH, DELETE | admin |
| `/api/gates/in` | `api/app/routes/gates.py` | GET, POST, PATCH, DELETE | admin |
| `/api/gates/out` | `api/app/routes/gates.py` | GET, POST, PATCH, DELETE | admin |
| `/api/settings` | `api/app/routes/settings.py` | GET, PATCH | admin |
| `/api/health` | `api/app/routes/health.py` | GET | public |

### 4. WebSocket Infrastructure

| File | Purpose |
|------|---------|
| `api/app/websocket/broadcaster.py` | Redis Pub/Sub bridge for multi-worker Gunicorn |
| `api/app/websocket/handlers.py` | `/ws/{gate_id}` endpoint with cookie auth |
| `api/app/websocket/connection_manager.py` | Connection registry per gate |

### 5. ARQ Workers

| File | Purpose |
|------|---------|
| `workers/settings.py` | Critical + Background worker settings |
| `workers/critical/print_worker.py` | print_ticket, print_receipt stubs |
| `workers/critical/snapshot_worker.py` | Camera snapshot download to local filesystem |
| `workers/background/settlement_worker.py` | Settlement file generation stub |
| `workers/background/cleanup_worker.py` | Old sessions and snapshots cleanup |
| `workers/background/notification_worker.py` | Telegram Bot API alerts |

### 6. Services

| File | Purpose |
|------|---------|
| `api/app/services/tariff.py` | Configurable tariff engine (not hardcoded) |
| `api/app/services/user.py` | User CRUD with password hashing |
| `api/app/services/gate.py` | Gate configuration service |

### 7. Protocol Layer (stdlib only)

| File | Purpose |
|------|---------|
| `protocols/passti/frame.py` | Frame builder/parser per spec |
| `protocols/passti/commands.py` | High-level PASSTI commands |
| `protocols/passti/transport.py` | EmoneyReaderTransport ABC |
| `protocols/compass/protocol.py` | Compass TCP protocol |
| `protocols/compass/parser.py` | STAT response parser |

### 8. Model Updates

| Model | Change |
|-------|--------|
| `EmoneyReader` | + `connection_type` field |
| `GateIn` | + `relay_mode` field |
| `GateOut` | + `relay_mode` field |

**Migration:** `1d087dbbd036_add_connection_type_and_relay_mode.py`

---

## Audio Assets Required

Place in `frontend/public/audio/`:

| # | Filename | Text | Trigger |
|---|----------|------|---------|
| 001 | `001_selamat_datang.mp3` | "Selamat Datang" | Valid entry |
| 002 | `002_ambil_tiket.mp3` | "Silakan Ambil Tiket" | Ticket button |
| 003 | `003_kartu_tidak_valid.mp3` | "Kartu Tidak Valid" | Invalid member |
| 004 | `004_member_tidak_aktif.mp3` | "Member Tidak Aktif" | Expired member |
| 005 | `005_tunggu_petugas.mp3` | "Mohon Tunggu Petugas" | Help button |
| 006 | `006_saldo_kurang.mp3` | "Saldo Tidak Cukup" | Low balance |
| 007 | `007_kartu_salah.mp3` | "Gunakan Kartu Sebelumnya" | Wrong card |
| 008 | `008_hubungi_petugas.mp3` | "Mohon Hubungi Petugas" | Timeout |
| 009 | `009_terima_kasih.mp3` | "Terima Kasih" | RFID exit |
| 010 | `010_pembayaran_berhasil.mp3` | "Pembayaran Berhasil" | E-money success |
| 011 | `011_transaksi_gagal.mp3` | "Transaksi Gagal" | Deduct failed |
| 012 | `012_waktu_habis.mp3` | "Waktu Habis" | No card timeout |

---

## Verification Results

| Test | Result |
|------|--------|
| Password hashing (bcrypt direct) | 5/5 passed |
| JWT token create/decode | 6/6 passed |
| Auth service authenticate_user | 6/6 passed |
| Tariff calculation engine | 10/10 passed |
| PASSTI frame builder/parser | 8/8 passed |
| Compass STAT parser | 13/13 passed |
| Model migration | Applied successfully |
| FastAPI app loading | All routes mounted |
| **Total tests** | **47/47 passed** |

---

## Decisions Made

1. **Password hashing:** Used `bcrypt` directly with `gensalt(rounds=12)` instead of `passlib[bcrypt]`. Passlib has a 72-byte backend detection bug with bcrypt >= 4.0.

2. **JWT dual tokens:** Access token (30min) + refresh token (7d), both httpOnly cookies. Refresh token rotation on every use.

3. **Token revocation:** Redis denylist with TTL matching token expiry. O(1) check.

4. **WebSocket auth:** Via existing `access_token` httpOnly cookie during HTTP upgrade.

5. **ARQ queue separation:** Two Redis keys (`arq:queue:critical`, `arq:queue:background`).

6. **EmoneyReaderTransport ABC:** Controller passthrough implemented now, direct serial stubbed.

7. **Camera snapshot:** Saved to `/var/lib/parking/snapshots/` locally.

8. **Relay mode:** `SINGLE` (default) vs `DUAL` per gate.

9. **Tariff engine:** Configurable via `TariffConfig` dataclass, not hardcoded. Default config in code for dev; production config via admin settings.

---

## Files Created/Modified

**Created:** 35+ new files across `api/app/`, `workers/`, `protocols/`, `api/tests/`, `protocols/tests/`

**Modified:**
- `api/app/main.py` — mount all routes and WebSocket
- `api/app/models/emoney_reader.py` — add `connection_type`
- `api/app/models/gate_in.py` — add `relay_mode`
- `api/app/models/gate_out.py` — add `relay_mode`

**Total lines of code:** ~3,500+

---

## Week 2 Exit Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `POST /api/auth/login` returns tokens in httpOnly cookies | Tested |
| 2 | `GET /api/auth/me` returns current user with valid cookie | Tested |
| 3 | `POST /api/auth/logout` clears cookies and revokes tokens | Tested |
| 4 | Admin-only routes return 403 for operator role | Tested |
| 5 | WebSocket `/ws/{gate_id}` authenticates and receives events | Implemented |
| 6 | ARQ critical worker processes `print_ticket` job | Implemented |
| 7 | ARQ background worker processes `send_telegram_alert` job | Implemented |
| 8 | PASSTI frame builder produces byte-perfect frames per spec | 8/8 tests pass |
| 9 | Compass `STAT` parser correctly extracts IN states and W/X data | 13/13 tests pass |
| 10 | Tariff engine calculates correct fee for all vehicle types | 10/10 tests pass |
| 11 | Alembic migration adds `connection_type` and `relay_mode` columns | Applied |
| 12 | All new modules import without circular dependency errors | Verified |
| 13 | FastAPI docs show all routes with auth requirements | Verified |

---

## Looking Ahead to Week 3

**Week 3 scope:** Frontend Foundation + Integration
- Nuxt 3 project setup with Element Plus, Pinia, Vue Router
- Login page (`/login`) with httpOnly cookie auth
- Pinia stores: `auth.js`, `website.js`, `gate.js`
- API client composables: `useApi.js`, `useCrud.js`
- WebSocket plugin with auto-reconnect
- POS page skeleton (`/`) with triple-method payment layout

---

*End of Week 2 Build Log*
