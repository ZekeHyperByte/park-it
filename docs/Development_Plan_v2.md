# E-Parking System V2 — Apex Architecture & Development Plan

> Version: 2.0 | Date: 2026-04-25 | Status: FINAL

---

## Executive Summary

E-Parking v2 is a ground-up rewrite of the v1 Laravel/PHP system. The goal is the apex of on-premise parking management: **sub-50ms gate response, guaranteed-delivery hardware IPC, offline-capable daemons, and zero vehicle trapping under any failure condition.**

**Developer:** Solo
**Capacity:** ~40 hours/week → 480 total hours over 12 weeks
**Timeline:** 12 weeks (3 months), fully sequential — no parallel workstreams
**Stack:** FastAPI · PostgreSQL · pgBouncer · Redis 7 · ARQ · Nuxt 3 · Python daemons · systemd · Nginx

> **Solo dev note:** Phases run back-to-back. The backend API must be stable before frontend begins. Daemons start after protocols are solid. Testing is integrated into each phase — no separate QA sprint.

---

## Core Design Mandates

1. **Gate first, everything else after.** Gate open fires before print/snapshot jobs are enqueued. Printer jam ≠ car stuck.
2. **Daemons are autonomous.** Redis/FastAPI/DB down → daemons operate from local SQLite cache. Self-heal on reconnect.
3. **Never trap a vehicle.** Any failure at gate-out → force-open + LOST_CONTACT flag + operator alert.
4. **Peripherals are best-effort.** Printer, camera, audio, LED failures are logged; gate is unaffected.
5. **Atomic writes for financial data.** Settlement files: write `.tmp` → fsync → rename. Corrupt files are impossible.

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Backend API | FastAPI (Python 3.12, async) | Async-native; handles concurrent gate events without blocking |
| Database | PostgreSQL 16 + SQLAlchemy 2 (async) | `SKIP LOCKED` for settlement; proper advisory locks; async ORM |
| Connection Pool | pgBouncer (transaction mode) | Prevents connection exhaustion under multi-gate load |
| Cache / Hot Path | Redis 7 (hash + sorted sets) | Member card + tariff lookups < 1ms; invalidated on admin change |
| IPC: Commands | Redis Streams (`parking.commands.{gate_id}` — ACK-based) | Guaranteed delivery to daemon; open_gate cannot be lost or replayed incorrectly |
| IPC: Events | Redis Pub/Sub (`parking.events.{gate_id}` — fire-and-forget) | Daemon telemetry (vehicle detected, card read, etc.) — loss is acceptable |
| Job Queue | ARQ (async, Redis-backed) | Print, snapshot, settlement, notification workers |
| Frontend | Nuxt 3 + Element Plus + Pinia | Proven in v1; SPA, SSR disabled |
| Auth | JWT + httpOnly cookies | Prevents XSS token theft; no token in localStorage |
| WebSocket Hub | FastAPI native (Starlette) | Single hub owned by API; daemons never serve WS directly |
| Reverse Proxy | Nginx | SSL, WS upgrade, static files, `proxy_read_timeout 3600s` |
| Services | systemd (one daemon per gate) | Auto-restart on failure |
| Dev Environment | Docker Compose | Full stack incl. pgBouncer, Redis, mock hardware server |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Nuxt 3 Frontend (SPA)                     │
│  POS · Admin · Reports · Device Mgmt · Settlement · Alerts  │
└────────────────────┬──────────────────────────┬─────────────┘
                     │ REST (JWT cookie)         │ WebSocket
                     ▼                           ▼
              [ Nginx Reverse Proxy ]
                     │
┌────────────────────▼──────────────────────────────────────┐
│            FastAPI Application                            │
│  Auth · Transactions · Gate Logic · Tariff · Member       │
│  Settlement · Alerts · WebSocket Hub · Stream Consumer    │
└──────────┬─────────────────────────────────────┬──────────┘
           │                                     │
  ┌────────▼────────┐              ┌─────────────▼──────────────────┐
  │   pgBouncer     │              │           Redis 7               │
  └────────┬────────┘              │  Streams:  gate_commands        │
  ┌────────▼────────┐              │  Pub/Sub:  gate_events          │
  │  PostgreSQL 16  │              │  Cache:    members, tariff      │
  └─────────────────┘              │  ARQ:      print/snap/settle    │
                                   └─────────────┬──────────────────┘
                            ┌────────────────────┘
                            │ Streams: parking.commands.{id} → Daemon (ACK)
                            │ Pub/Sub: parking.events.{id}   ← Daemon (fire-and-forget)
               ┌────────────┴─────────────────────┐
               │                                  │
  ┌────────────▼────────────┐    ┌────────────────▼────────────────┐
  │      gate_in.py          │    │         gate_out.py              │
  │   (one per entry gate)   │    │     (one per exit gate)          │
  │  • Sensor loop IN1–IN4  │    │  • Sensor loop IN1–IN4          │
  │  • RFID 125kHz reads    │    │  • UHF/RFID reads               │
  │  • Audio · LED          │    │  • PASSTI full protocol          │
  │  • Gate trigger         │    │  • Audio · LED                  │
  │  • Offline mode (SQLite)│    │  • Gate trigger                 │
  │  • Dead-man timer       │    │  • Offline mode (SQLite)        │
  │  • Sensor watchdog      │    │  • Dead-man timer · watchdog    │
  │  • HW heartbeat (30s)   │    │  • HW heartbeat (30s)           │
  └────────────┬────────────┘    └────────────────┬────────────────┘
               │                                  │
  ┌────────────▼──────────────────────────────────▼────────────────┐
  │                     Physical Hardware                          │
  │  Gate Controller (1-relay PULSE or 2-relay OPEN_CLOSE)        │
  │  RFID 125kHz · UHF Long-Range · PASSTI E-Money Readers        │
  │  Thermal Printers (ESC/POS) · LED Displays · Audio Module     │
  │  IP Cameras · Loop Sensors                                    │
  └─────────────────────────────────────────────────────────────────┘
```

---

## Gate Flows

### Payment Methods

| Method | Gate-In | Gate-Out |
|---|---|---|
| **Cash** | Button pressed → print ticket → gate opens | Barcode scan → fee calculated → cash paid → gate opens |
| **RFID (Member)** | Card tap → validate → no ticket → gate opens | Card tap → zero cost → gate opens |
| **E-Money** | Card tap → check balance ≥ minimum → gate opens (deduct at exit) | Barcode scan → card tap → deduct fee → gate opens |

### Gate-In: Cash
```
IN1 ON → snapshot job enqueued → WS: "Vehicle waiting"
IN2 ON (button) → CREATE transaction (CASH) → OPEN GATE → enqueue print ticket
Vehicle passes IN3 → close gate
```

### Gate-In: RFID
```
IN1 ON → RFID tap (*W12345678#)
Valid member → CREATE transaction (RFID) → OPEN GATE → enqueue snapshot
Expired/Invalid → play audio → gate stays closed
```

### Gate-In: E-Money
```
IN1 ON → driver taps PASSTI reader → GET_BALANCE
Balance ≥ min_balance → CREATE transaction (EMONEY, card_number stored) → OPEN GATE
Balance insufficient → play audio → gate stays closed
[Optional: IN2 pressed → also enqueue print ticket]
NOTE: No deduction at entry. Fee is unknown until exit.
```

### Gate-Out: Cash
```
Exit sensor ON → snapshot job → WS: "Vehicle waiting — scan barcode"
Operator scans barcode → calculate fee → collect cash → POST /checkout
OPEN GATE → enqueue print receipt
```

### Gate-Out: RFID (Zero cost)
```
Exit sensor ON → snapshot job → card tap
Lookup active transaction → UPDATE (status=COMPLETED, fee=0) → OPEN GATE
```

### Gate-Out: E-Money
```
Exit sensor ON → snapshot job → operator scans barcode → calculate fee
Driver taps PASSTI reader → DEDUCT(amount=fee)
├── SUCCESS → CREATE emoney_transaction → UPDATE parking_transaction → OPEN GATE → print receipt
├── TIMEOUT → retry (configurable) → GET_LAST_TRANSACTION
│     ├── Confirmed deducted → treat as SUCCESS
│     └── Not deducted → CORRECTION_FAILED → FORCE OPEN + operator alert
└── HARD ERROR → CORRECTION_FAILED → FORCE OPEN + operator alert
```

---

## Hardware Controller Abstraction

Both controller types (1-relay and 2-relay) use the **same daemon**, configured via DB:

| gate_mode | Behavior | Typical Use |
|---|---|---|
| `PULSE` | Send open command · wait N ms | 1-relay, spring-return barriers (entry) |
| `OPEN_CLOSE` | Send open command · wait IN3 · send close command | 2-relay, motorized barriers (exit) |

Config per gate: `open_command`, `close_command`, `pulse_duration_ms`, `gate_open_timeout_s`

---

## Reliability Features

| Feature | Implementation |
|---|---|
| Daemon offline mode | Local SQLite cache (member cards, gate config). Queue local transactions. Sync on reconnect. |
| Gate-first ordering | open_gate Pub/Sub fires → then ARQ jobs enqueued. Never blocked by peripherals. |
| Dead-man timer | Gate auto-closes if IN3 never fires within `gate_open_timeout_s`. Operator alerted. |
| Sensor watchdog | IN1 stuck ON beyond `sensor_stuck_s` → operator alert. Daemon does not freeze. |
| Hardware heartbeat | Daemon PINGs controller every 30s. No response after 3× → operator alert. |
| Settlement atomic write | Write `.tmp` → fsync → rename. Crash-safe; file either exists complete or not at all. |
| NTP check at startup | FastAPI refuses to start if clock drift > 1 second. Prevents billing timestamp errors. |
| pgBouncer | Sits between FastAPI and PostgreSQL. Prevents connection exhaustion under load. |
| Redis hot-path cache | Member cards + tariffs cached in Redis (TTL 300s / 60s). Invalidated on admin write. |
| SKIP LOCKED | Settlement job uses PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED`. No double-processing. |

---

## Database — New Tables / Key Additions

```sql
-- parking_transactions (additions)
payment_method       ENUM('CASH','RFID','EMONEY')
emoney_card_number   VARCHAR(32) NULLABLE
entry_snapshot_id    BIGINT NULLABLE FK → snapshots
exit_snapshot_id     BIGINT NULLABLE FK → snapshots

-- emoney_transactions (NEW)
parking_transaction_id, card_number, amount_deducted,
balance_before, balance_after,
deduct_status ENUM('SUCCESS','TIMEOUT','CORRECTION_VERIFIED','CORRECTION_FAILED'),
retry_count, verified_at

-- operator_alerts (NEW)
gate_type, gate_id, alert_type, message, is_resolved, resolved_by, resolved_at

-- health_checks (NEW)
component, status ENUM('OK','DEGRADED','DOWN'), latency_ms, checked_at

-- gate_ins / gate_outs (additions)
gate_mode, open_command, close_command, pulse_duration_ms,
gate_open_timeout_s, sensor_stuck_s,
min_emoney_balance, allow_cash, allow_rfid, allow_emoney
```

---

## Development Timeline — 12 Weeks (Solo)

> **Capacity:** 40 hours/week · 480 hours total
> **Phases are sequential.** No parallel tracks — one person does everything in order.
> Testing is done at the end of each phase before moving to the next. No dedicated QA sprint.

---

### Phase 1 — Foundation & Infrastructure (Weeks 1–2) · ~80h

**Goal:** Rock-solid base. Nothing else starts until this is done and tested.

| Week | Daily Focus | Tasks |
|---|---|---|
| **Week 1** | Mon–Wed: Project skeleton | Monorepo layout · `pyproject.toml` · Docker Compose (FastAPI + PostgreSQL + pgBouncer + Redis) · `.env` config with pydantic-settings · base logging |
| | Thu–Fri: DB & migrations | Full DB schema (all tables including v2 additions) · Alembic setup · seed data · migration roll-forward/rollback verified |
| **Week 2** | Mon–Tue: Auth | JWT login/logout/refresh · httpOnly cookie · RBAC middleware · `/api/me` |
| | Wed–Thu: Infrastructure | Redis Streams consumer group setup · ARQ worker process · FastAPI `/api/health` endpoint · NTP startup check · pgBouncer config |
| | Fri: Verify | `docker compose up` → everything green · auth flow end-to-end · migration smoke test on fresh DB |

**Exit criteria:** Dev environment boots clean. Auth works. DB schema frozen. Redis Streams consumer group created.

---

### Phase 2 — Backend Core (Weeks 3–5) · ~120h

**Goal:** All business logic implemented and tested. API-complete before touching frontend or hardware.

> **V1 carry-over:** Port logic from these Laravel controllers — don't reinvent: `ParkingTransactionController.php` (fee calc, barcode search, gate-in/out flow), `MemberController.php` + `MemberRenewalController.php`, `ReportController.php` (shift/daily reports), `JenisKendaraanController.php` (tariffs). The `ParkingTransaction` model's field set (`is_member`, `tarif`, `shift_id`, `plat_nomor`, etc.) is the baseline for the v2 schema — add `payment_method`, `emoney_card_number`, `entry_snapshot_id`, `exit_snapshot_id` on top.

| Week | Daily Focus | Tasks |
|---|---|---|
| **Week 3** | Mon–Tue: Transactions | Parking transaction CRUD · status lifecycle (ACTIVE → COMPLETED → LOST_CONTACT) · partial unique index enforcement |
| | Wed: Tariff engine | Flat/progressive pricing · overnight modes (24h / midnight) · max daily cap · lost ticket penalty |
| | Thu–Fri: Gate-In API | `vehicle_detected` handler · `card_read` handler (RFID lookup with Redis cache) · `open_gate` Pub/Sub publisher · member card Redis hot-path cache |
| **Week 4** | Mon–Tue: Gate-Out API | Exit detection handler · barcode/plate search · fee calculation · POS checkout endpoint |
| | Wed: RFID & E-Money exit | RFID zero-cost exit · e-money gate-out handler · PASSTI deduct state machine · LOST_CONTACT → force-open path |
| | Thu: Supporting models | `emoney_transactions` CRUD · `operator_alerts` publisher · `health_checks` writer |
| | Fri: Shift logic | Shift open/close · shift assignment by time-in · per-shift reconciliation |
| **Week 5** | Mon–Tue: Members & config | Member CRUD · vehicle linking · renewals · group pricing · area & tariff config API |
| | Wed–Thu: Settlement worker | ARQ job · atomic file write (`.tmp` → fsync → rename) · `SKIP LOCKED` · bank file format · batch limits |
| | Fri: Test week | Unit tests: all tariff edge cases · integration tests: gate-in/out flows · Redis cache hit/miss · e-money state machine · settlement file validation |

**Exit criteria:** All 30+ API endpoints return correct data. Tariff engine passes all edge case tests. Settlement file matches bank spec exactly.

---

### Phase 3 — Hardware Protocols & Daemons (Weeks 6–8) · ~120h

**Goal:** Real gate communication. All code tested against mock hardware server before touching real controllers.

> **V1 carry-over:** The byte-level protocol commands are **production-validated** — port them directly:
> - **Compass** (`parking.py`): poll `\xa6STAT\xa9`, trigger `\xa6TRIG1\xa9`, audio `\xa6MT000NN\xa9`, LED `\xa6D...\xa9`
> - **ENET** (`parking-enet.py`): poll `:INFO;`, trigger `:OPEN1;`, audio `:PLAYTRACKN;`
> - **Sensor patterns**: `IN1ON`/`IN2ON`/`IN3OFF` byte strings — identical across both protocols
> - **ESC/POS print sequence** (align center → double-height name → align left → CODE39 barcode → cut) is correct — port to `escpos.py`
> - **Audio track map**: 2=take ticket, 3=invalid card, 5=need help, 6=thank you, 7=welcome, 11=expiring in 5d, 12=expiring in 1d, 13=expired, 14=unclosed
> - **Sensor state machine** (IN1 → wait button/card → gate trigger → wait IN3 → reset) is the exact loop to wrap in `asyncio`
> - Both Compass and ENET variants must be supported — configure per-gate via DB (`protocol` field)

| Week | Daily Focus | Tasks |
|---|---|---|
| **Week 6** | Mon: Mock server | Hardware simulation server (TCP/serial mock) — all tests run against this |
| | Tue–Wed: Protocol libs | `frame.py` (STX/LRC checksum) · `compass.py` · `enet.py` · `serial_proto.py` (`*..#` framing) · unit tests for all |
| | Thu–Fri: Printer + PASSTI | `escpos.py` (text, CODE39 barcode, cut, buzzer) · `passti.py` (INIT, GET_BALANCE, DEDUCT, GET_LAST_TRANSACTION, CANCEL_CORRECTION, encryption) |
| **Week 7** | Mon–Wed: gate_in.py | Sensor loop (IN1–IN4) · RFID card reads · audio commands · LED text · gate trigger (PULSE/OPEN_CLOSE) · dead-man timer · sensor watchdog · hardware heartbeat (30s) |
| | Thu–Fri: gate_in offline mode | Local SQLite cache (member cards + gate config) · offline transaction queue · auto-sync on Redis reconnect |
| **Week 8** | Mon–Wed: gate_out.py | Everything from gate_in + PASSTI full integration + e-money deduct state machine with retry loop |
| | Thu: gate_out offline mode | Same offline pattern as gate_in |
| | Fri: Integration tests | Daemon ↔ FastAPI ↔ Redis full flow · offline mode simulation · deduct retry exhaustion · heartbeat timeout · dead-man trigger |

**Exit criteria:** Both daemons pass full integration suite against mock server. Offline mode confirmed: Redis down → daemon continues → transactions queue → sync on reconnect.

---

### Phase 4 — Frontend (Weeks 9–11) · ~120h

**Goal:** Complete Nuxt 3 SPA wired to the real API.

> **V1 carry-over:** A Nuxt 3 frontend already exists at `parking-system/nuxt3-fe/`. Do not start from scratch:
> - `index.vue` (~25 KB) — substantial POS screen with transaction search, fee display, gate buttons. **Port and extend** for e-money flow.
> - `GateInApp.vue` — plate/vehicle/gate form. **Port directly.**
> - `components/` — 33 components to audit for reuse.
> - `setting.vue`, `device.vue`, `member.vue`, `transaksi.vue` are stubs only — build these.
> Auth must be re-wired from Sanctum token headers to the v2 JWT httpOnly cookie API.

| Week | Daily Focus | Tasks |
|---|---|---|
| **Week 9** | Mon: Scaffold | Nuxt 3 init · Element Plus · Pinia · `$fetch` with credentials · route guards · layouts (default sidebar, login bare) |
| | Tue: Auth + WebSocket | Login page · silent refresh interceptor · logout · WebSocket plugin (exponential backoff, heartbeat, disconnect banner) |
| | Wed–Fri: POS screen | `index.vue` — transaction search (barcode/plate), fee display, cash payment flow, RFID tap flow, e-money tap flow, gate control buttons, camera snapshot, keyboard shortcuts (`-` `+` `*` `/` F10–F12) |
| **Week 10** | Mon: Gate-In screen | `GateInApp.vue` — plate entry, vehicle type, gate selection, transaction creation |
| | Tue–Wed: Admin settings | `setting.vue` — 6 tabs: General, Vehicle Types/Tariffs, Users, Shifts, Areas, Backup/Restore |
| | Thu: Device management | `device.vue` — 5 tabs: Cameras, Printers, POS, Gate Out, Gate In (CRUD + test actions + status) |
| | Fri: Transactions | `transaksi.vue` — full CRUD table, filters, manual entry, ManualOpenLog audit trail |
| **Week 11** | Mon–Tue: Members | `member.vue` — member CRUD, group management, renewals, daily/summary income reports |
| | Wed: Reports | `report.vue` + e-money breakdown, settlement status, snapshot browser, operator attendance, user log |
| | Thu: Alerts & settlement UI | Operator alerts dashboard · settlement download/upload (.OK/.NOK) · status tracking |
| | Fri: E2E test pass | Login → gate-in → gate-out (cash) → gate-out (e-money) → settlement — all flows green |

**Exit criteria:** Every page functional against staging API. POS handles all 3 payment methods. WebSocket reconnects cleanly.

---

### Phase 5 — Integration, Deployment & UAT (Week 12) · ~40h

**Goal:** Ship it. On real hardware. Signed off.

| Day | Tasks |
|---|---|
| **Mon** | systemd service files (API, ARQ worker, gate_in×N, gate_out×N) · Nginx config (WS upgrade, SSL, static assets, timeouts) · Docker Compose production profile |
| **Tue** | Deploy to production server · pgBouncer tuning · Redis maxmemory policy · log rotation config |
| **Wed** | Hardware staging: real controllers, real printers, real e-money readers — all 6 gate flows tested on physical hardware |
| **Thu** | UAT with operators · bug fixes (time-boxed: critical bugs only) · load test: concurrent gate-in/out, WebSocket connections |
| **Fri** | OpenAPI docs review · operator manual finalized · deployment runbook · UAT sign-off |

**Exit criteria:** All 6 gate flows work on real hardware. Operators can use the system without assistance. Sign-off received.

---

## Timeline Summary

```
Week:  1    2    3    4    5    6    7    8    9    10   11   12
       ├────┤────┤────┤────┤────┤────┤────┤────┤────┤────┤────┤
Ph 1   ████████                                                   Foundation
Ph 2             ████████████                                     Backend
Ph 3                         ████████████                        Daemons
Ph 4                                     ████████████            Frontend
Ph 5                                                 ████         Deploy/UAT
       ├────┤────┤────┤────┤────┤────┤────┤────┤────┤────┤────┤
```

> Fully sequential. Each phase must pass its own exit criteria before next phase starts.
> Hardware should be available by Week 8 at the latest for Phase 3 real-hardware validation.
> If PASSTI vendor docs are delayed — flag this in Week 1. It is the highest-risk dependency.

---

## Effort Summary

| Phase | Weeks | Hours (~40h/wk) | Focus |
|---|---|---|---|
| 1. Foundation | 1–2 | ~80h | Infrastructure, DB, auth |
| 2. Backend Core | 3–5 | ~120h | All business logic + API |
| 3. Hardware / Daemons | 6–8 | ~120h | Protocols + daemons + offline mode |
| 4. Frontend | 9–11 | ~120h | Full Nuxt 3 SPA |
| 5. Deploy / UAT | 12 | ~40h | Production + sign-off |
| **Total** | **12 weeks** | **~480h** | |

> 480 hours is tight but achievable for a skilled full-stack developer who knows FastAPI, Nuxt 3, and Python serial/TCP programming. The largest risk is PASSTI protocol complexity — budget extra time in Week 6 if vendor documentation is incomplete.

## Solo Developer Responsibilities

One person owns everything:

| Area | Responsibilities |
|---|---|
| Backend | FastAPI architecture, DB schema, Alembic, business logic, Redis, ARQ workers |
| Hardware | Protocol libraries (Compass, ENET, PASSTI, ESC/POS), both daemons, offline mode |
| Frontend | Nuxt 3 SPA, all pages, WebSocket plugin, POS state machine |
| DevOps | Docker Compose, pgBouncer, systemd, Nginx, SSL, production deploy |
| Testing | Unit tests, integration tests, E2E (Playwright), hardware staging |
| Docs | OpenAPI, operator manual, deployment runbook |

## Risk Register (Solo)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PASSTI vendor docs incomplete | Medium | High — blocks e-money entirely | Request full spec + sample capture in Week 1. Add 1-week buffer in Phase 3. |
| Hardware arrives late | Medium | High — blocks Phase 3 real test | Use mock hardware server for all unit/integration tests. Real hardware needed only end of Week 8. |
| Scope creep (new features) | High | Medium | Anything not in this document is a change request. Log it, defer to post-UAT. |
| Energy/burnout (solo) | Medium | High | Week 12 is intentionally lighter. Take 1 reset day per phase if needed — it's built into the buffer. |

---

## Included in Delivery

- Full source code (client-preferred license)
- All 6 gate flows: cash / RFID / e-money × gate-in / gate-out
- FastAPI backend with async PostgreSQL + pgBouncer + Redis
- Nuxt 3 frontend SPA with all operational pages
- Protocol libraries: Compass, ENET, Serial `*..#`, PASSTI, ESC/POS, Frame
- 2 hardware daemons: `gate_in.py` + `gate_out.py` (with offline mode)
- 4 ARQ workers: print, snapshot, settlement, notification
- Redis Streams IPC + Pub/Sub gate commands
- Hardware simulation server for CI/CD
- Docker Compose dev environment
- systemd + Nginx production configuration
- Unit, integration, E2E test suites
- OpenAPI documentation + operator manual + deployment guide
- 30-day post-deployment warranty (bug fixes)

## Not Included (Add-ons)

- Hardware procurement (gate controllers, PASSTI readers, printers, cameras)
- Cloud/VPS hosting costs
- SSL certificates (Let's Encrypt is free)
- Mobile app (iOS/Android)
- Data migration from v1
- On-site installation travel costs
- Extended warranty beyond 30 days ($500/month)

---

*Document: E-Parking System V2 — Apex Development Plan*
*Created: 2026-04-25*
