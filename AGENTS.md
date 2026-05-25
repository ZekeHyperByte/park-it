# E-Parking v2 — Agent Guide

> This file contains project context for AI agents. Read before modifying code.

---

## Project Overview

E-Parking v2 is a parking management system for Indonesian e-money cards (Mandiri eMoney, BRI Brizzi, BNI TapCash, BCA Flazz, etc.) using the PASSTI Reader from PT Softorb.

**Stack:** FastAPI (Python) + PostgreSQL + Redis + Nuxt 3 (Vue) + systemd
**Hardware:** Compass/ENET controllers, serial e-money readers, thermal printers, barcode scanners, cameras

---

## Architecture

### Unified Gate Model (Important!)

The system uses a **single `Gate` model** replacing the old `GateIn`/`GateOut` split:

| Old | New |
|-----|-----|
| `gate_ins` table | `gates` table with `direction='IN'` |
| `gate_outs` table | `gates` table with `direction='OUT'` |
| `/api/gates/in` | `/api/gates?direction=IN` |
| `/api/gates/out` | `/api/gates?direction=OUT` |
| `GateIn` / `GateOut` models | `Gate` model only |

**Old tables (`gate_ins`, `gate_outs`) and routes were dropped.** See migration `f0bd4bac1599`.

### Data Flow

```
Vehicle enters → Controller (IN1 sensor) → GateInDaemon → Redis Pub/Sub → API
                                                              ↓
                                            Welcome audio + LED (configurable)
                                                              ↓
                                                         Transaction created
                                                              ↓
                                                   Entry snapshot enqueued (ARQ)
                                                              ↓
                                              print_ticket_then_open → gate opens

Vehicle exits  → Controller (IN1 sensor) → GateOutDaemon → Redis Pub/Sub → API
                                                              ↓
                                                         POS notified (WebSocket)
                                                              ↓
                                               Operator pays Cash/RFID/E-Money
                                                              ↓
                                    CASH: Receipt prints (ARQ), NO auto gate open
                                    CASH: Operator presses Space/button → open gate
                                    RFID/EMONEY: Auto open gate (pre-verified)
```

### E-Money Payment Architecture

The system supports **two e-money payment paths** for maximum deployment flexibility:

**1. Booth Bridge Path (Primary — attended gates)**
```
Card Tap → Booth Bridge (serial) → parses PASSTI response
                                              ↓
                                   Calls API /emoney/booth-result (HTTP + API key)
                                              ↓
                                   API: process_emoney_result → creates EmoneyTransaction
                                              ↓
                                   Redis Stream: open_gate → GateOutDaemon → gate opens
```

**2. Manless Path (Fallback — unmanned gates)**
```
Card Tap → GateOutDaemon → ControllerPassthroughTransport → PASSTI reader via controller
                                              ↓
                                   Redis Pub/Sub: DeductResultEvent
                                              ↓
                                   API Event Consumer → process_emoney_result
                                              ↓
                                   Redis Stream: open_gate → GateOutDaemon → gate opens
```

**3. Entry Gate E-Money**
```
Card Tap → GateInDaemon → ControllerPassthroughTransport → PASSTI reader
                                              ↓
                                   Redis Pub/Sub: PasstiCardTapEvent
                                              ↓
                                   API: CheckBalanceCommand → daemon validates
                                              ↓
                                   Driver presses button → EmoneyPrintDecisionEvent
                                              ↓
                                   API: creates transaction → Redis Stream: open_gate
```

**Key components:**
- `api/app/middleware/api_key.py` — `require_api_key` for booth bridge → API auth
- `api/app/routes/payments.py` — `POST /api/payments/emoney/booth-result`
- `api/app/services/event_consumer.py` — Server-side Redis Pub/Sub event consumer
- `booth_bridge/websocket_server.py` — Parses PASSTI + calls API directly
- `shared/events.py` — `EmoneyPaymentConfirmedCommand`, `EmoneyPrintDecisionEvent`

### Booth Architecture

Each exit gate has a **Booth PC** with serial devices:
- E-money reader (PASSTI via serial)
- Receipt printer (ESC/POS via serial)
- Barcode scanner (HID/serial)

The **Booth Bridge** (`booth_bridge/main.py`) runs on each booth PC, exposing serial devices via WebSocket (`ws://localhost:5678`). The POS web app connects to this bridge for e-money taps and printing.

**Booth Bridge API Integration:**
- The booth bridge parses PASSTI responses directly (not the frontend)
- On successful deduct, it calls `POST /api/payments/emoney/booth-result` with the `X-API-Key` header
- This removes the browser from the critical payment path
- Configured via `api_base_url` and `api_key` in `/etc/parking/booth.json`

---

## Directory Structure

```
parking-system-v2/
├── api/                          # FastAPI backend
│   ├── app/
│   │   ├── main.py               # App factory (creates FastAPI app)
│   │   ├── models/               # SQLAlchemy models
│   │   │   ├── gate.py           # Unified Gate model (replaces GateIn/GateOut)
│   │   │   ├── parking_transaction.py
│   │   │   └── ...
│   │   ├── routes/               # API route modules
│   │   │   ├── gates_unified.py  # /api/gates (CRUD for unified Gate)
│   │   │   └── ...
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── services/             # Business logic
│   │   └── websocket/            # WebSocket handlers
│   ├── alembic/versions/         # Database migrations
│   └── database.py               # Async SQLAlchemy engine/session
├── daemons/                      # Gate controller daemons
│   ├── cli.py                    # UNIFIED ENTRY POINT (queries DB, starts daemon)
│   ├── base.py                   # Abstract base daemon (Redis Streams + Pub/Sub)
│   ├── gate_in.py                # Entry gate state machine
│   └── gate_out.py               # Exit gate state machine
├── booth_bridge/                 # Booth PC serial-to-WebSocket bridge
│   ├── main.py                   # Entry point
│   ├── serial_manager.py
│   └── websocket_server.py
├── workers/                      # ARQ background/critical workers
├── frontend/                     # Nuxt 3 frontend
│   ├── pages/
│   │   ├── index.vue             # POS page (gate out)
│   │   ├── device.vue            # Device management (gates, booths, cameras)
│   │   └── ...
│   ├── stores/
│   │   ├── website.js            # Reference data cache (gates, vehicle types)
│   │   ├── gate.js               # POS transaction state
│   │   └── auth.js               # Auth state
│   └── composables/
│       ├── useApi.js             # fetch wrapper with httpOnly cookies
│       └── useCrud.js            # CRUD composable for DataTable
├── protocols/                    # Hardware protocols
│   ├── compass/                  # Compass controller protocol
│   └── passti/                   # PASSTI e-money reader protocol
├── shared/                       # Shared utilities (logs, config, Redis, events)
├── scripts/                      # Utility scripts
│   ├── dev-start.sh              # Development environment start
│   ├── dev-stop.sh               # Development environment stop
│   ├── seed.py                   # Dev database seeding
│   ├── enable-gate-daemons.sh    # Auto-enable systemd daemons from DB
│   ├── preflight_check.py        # Pre-deployment checks
│   └── deploy_hardware.py        # Generates systemd service files
├── systemd/                      # Production systemd unit files
│   ├── parking-api.service
│   ├── parking-daemon-gate-in@.service   # Template: ExecStart=python -m daemons.cli --gate-id %i
│   ├── parking-daemon-gate-out@.service  # Template: ExecStart=python -m daemons.cli --gate-id %i
│   ├── parking-worker-critical.service
│   ├── parking-worker-bg.service
│   └── booth-bridge.service
├── installer/                    # Production installers (NEW)
│   ├── server/                   # Full server stack installer
│   ├── booth_pc/                 # Minimal booth PC installer
│   └── booth_with_server/        # Server + local booth combo
└── tests/                        # Test suites
    ├── e2e/                      # End-to-end tests
    └── unit/                     # Unit tests
```

---

## Key Conventions

### Database
- Use **async SQLAlchemy** (`asyncpg` driver)
- Never import `api.database` from `daemons/` — create independent engines
- All datetime columns use `DateTime(timezone=True)`
- JSONB for flexible configs (e.g., `Gate.hardware_config`)

### Models
- All models inherit from `Base` + `IntPKMixin` + `TimestampMixin`
- Foreign keys use `BigInteger` (not `Integer`) for consistency
- Relationships must specify `foreign_keys=[...]` when ambiguous

### API
- All routes prefixed with `/api`
- Auth via httpOnly JWT cookies (not localStorage)
- Responses use `SuccessResponse` / `ErrorResponse` wrappers
- Admin routes use `require_admin`, operator routes use `require_operator`

### Frontend
- Uses **relative API URLs** (`/api/gates`) — not hardcoded `localhost:8000`
- `apiBaseUrl` defaults to `''` in `nuxt.config.ts` so nginx proxy works
- Stores use Pinia with `useApi()` composable for auth fetch

### Daemons
- **ALWAYS use `daemons/cli.py`** as the entry point
- `systemd` templates use: `ExecStart=python -m daemons.cli --gate-id %i`
- The CLI queries the DB by gate code, auto-detects direction, starts correct daemon
- Daemons communicate with API via Redis (Pub/Sub for events, Streams for commands)
- Heartbeat every 30 seconds — daemons/base.py publishes state in heartbeat for monitoring

### Exit Flow (Two-Step Cash)
- Cash payment does **NOT** auto-open the gate (Task 4 change)
- Operator pays → receipt prints (ARQ worker) → operator presses **Space** or clicks button → `POST /api/gates/{id}/open` → Opens via Redis Stream
- RFID and e-money remain auto-open (pre-verified methods)
- New endpoint: `POST /api/gates/{id}/open` with `GateControlRequest(reason="operator")`

### Entry Flow
- `gate_in.py` plays configurable welcome audio on vehicle detection (AudioConfig.welcome_track, default track 1)
- LED shows "Selamat Datang" on vehicle arrival (configurable via hardware_config.led.enabled)
- Ticket success/failure use configurable tracks (ticket_track/error_track)
- DUAL relay mode: gate closes after vehicle passes through (TRIG2)

---

## Common Tasks

### Add a New Gate
1. Open web UI → Device → Gates → Add
2. Fill: name, code, direction, controller host/port, hardware config
3. Run `sudo systemctl enable --now parking-daemon-gate-in@<CODE>` (or `gate-out`)

### Enable All Gate Daemons Automatically
```bash
# Preview commands
./scripts/enable-gate-daemons.sh

# Actually run them
./scripts/enable-gate-daemons.sh --run
```
This script reads all gates from the database and generates the correct `systemctl enable --now` commands.

### Development Start
```bash
./scripts/dev-start.sh          # Start everything (Docker infra + API + frontend)
./scripts/dev-stop.sh           # Stop services
./scripts/dev-stop.sh --infra   # Stop Docker infra too
```

### Database Migration
```bash
cd api && alembic revision -m "description"
# Edit the generated migration, then:
alembic upgrade head
```

### Seed Development Data
```bash
python scripts/seed.py
```
**Note:** `seed.py` uses the **unified `Gate` model** (not old `GateIn`/`GateOut`).

---

## Important Files for Agents

| File | Purpose |
|------|---------|
| `api/app/models/gate.py` | Unified Gate model — source of truth for gate config |
| `api/app/schemas/gate.py` | HardwareConfig, AudioConfig (welcome/ticket/error track) |
| `api/app/schemas/gate_control.py` | GateControlRequest/Response for manual open/close |
| `daemons/cli.py` | Daemon runner — reads gate config from DB |
| `daemons/base.py` | BaseDaemon — Redis Streams consumer + Pub/Sub publisher + heartbeat state |
| `daemons/gate_in.py` | Entry gate state machine — welcome audio/LED on vehicle detection |
| `daemons/gate_out.py` | Exit gate state machine — receipt printing via ARQ worker |
| `api/app/main.py` | FastAPI app factory — where routers are registered |
| `frontend/nuxt.config.ts` | Frontend config — `apiBaseUrl`, modules |
| `frontend/stores/gate.js` | POS transaction state — awaitingGateOpen, openGate() |
| `frontend/stores/website.js` | Gate cache — fetches `/api/gates?direction=IN/OUT` |
| `frontend/pages/index.vue` | POS page — two-step flow (pay → Space to open gate) |
| `frontend/pages/gate-in.vue` | Gate-in monitor — real-time WebSocket state, vehicle counts |
| `shared/config.py` | Settings — loaded from `.env` via pydantic-settings |
| `shared/events.py` | All Redis IPC event/command models |
| `api/alembic/versions/` | All DB migrations — read these before schema changes |
| `api/app/middleware/api_key.py` | API key auth for booth bridge → machine-to-machine |
| `api/app/routes/gates_unified.py` | Gate CRUD + `POST /{id}/open` `POST /{id}/close` |
| `api/app/routes/payments.py` | Payment routes including `/cash` (no auto-open) |
| `api/app/services/payment.py` | Cash/RFID/e-money orchestration — cash does NOT send OpenGateCommand |
| `api/app/services/event_consumer.py` | Server-side Redis Pub/Sub — handles vehicle_detected for exit snapshots |
| `api/app/services/transaction.py` | Transaction lifecycle — enqueues entry snapshot on create |
| `workers/critical/print_worker.py` | print_ticket + print_receipt ARQ jobs (ESC/POS templates) |
| `booth_bridge/websocket_server.py` | PASSTI parsing + direct API calls + print_receipt handler |
| `daemons/tests/test_gate_in_audio.py` | Tests for welcome audio, LED display, DUAL relay close |
| `api/tests/test_gate_control_routes.py` | Tests for manual open/close API endpoints |

---

## Deployment Topology (2 IN + 2 OUT)

```
┌─────────────────────────────────────────────────────────┐
│                    SERVER PC                             │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────┐   │
│  │ PostgreSQL │  │ Redis      │  │ FastAPI (nginx) │   │
│  │ port 5432  │  │ port 6379  │  │ port 80         │   │
│  └────────────┘  └────────────┘  └─────────────────┘   │
│                                                          │
│  Gate-In Daemon @GIN01   Gate-In Daemon @GIN02          │
│  Gate-Out Daemon @GOUT01                                │
│                                                          │
│  Booth Bridge (Booth 1) ← local serial devices          │
│  ws://localhost:5678                                    │
└─────────────────────────────────────────────────────────┘
                           │ HTTP
              ┌────────────┴────────────┐
              ▼                         ▼
     ┌───────────────┐         ┌───────────────┐
     │ BOOTH PC 2    │         │ ADMIN BROWSER │
     │ Booth Bridge  │         │ http://server │
     │ ws://localhost│         └───────────────┘
     │ :5678         │
     └───────────────┘
```

---

## Testing

```bash
# Backend tests
cd api && pytest

# Frontend tests
cd frontend && npm test

# Full test suite
./scripts/run-all-tests.sh    # If this exists, otherwise run individually
```

---

## Contact / Ownership

- **Repository:** `<your-repo-url>`
- **Deployment docs:** `installer/*/README.md`
- **Operations runbook:** `docs/OPERATIONS_RUNBOOK.md`
- **Field install guide:** `docs/FIELD_TECH_GUIDE.md`

---

*Last updated: May 6, 2026*
*Version: 2.3.0*

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Built from 413 v2 source files (3,512 nodes, 4,937 edges, 375 communities). Key god nodes: `GateOutDaemon` (68), `GateInDaemon` (62), `BaseDaemon` (28), `EventConsumer` (23), `CompassTransport` (18).

**Maintenance:**
- `.graphifyignore` mirrors `.gitignore` — add new large/noise dirs to both files
- After code changes, run `graphify update .` (AST-only, no API cost)
- After adding docs/plans, run full rebuild: `rm -rf graphify-out/` then invoke `/graphify .`
- The graph is gitignored — each developer builds their own

**Navigation:**
- Read `graphify-out/GRAPH_REPORT.md` for god nodes, surprising connections, community map
- Navigate `graphify-out/wiki/index.md` for structured community articles
- Query: `graphify query "<question>"`, `graphify path "A" "B"`, `graphify explain "<concept>"`

## @RTK.md

RTK (Rust Token Killer) is installed globally for shell command output compression. It reduces token usage by 60-90% on common dev commands.

## caveman

Want it always on? Add this to agent instructions:

```
You are caveman. Active every response. Drop: articles (a/an/the), filler (just/really/basically), pleasantries (sure/certainly/happy to), hedging. Fragments OK. Short synonyms. Technical terms exact. Pattern: [thing] [action] [reason]. [next step]. Code blocks unchanged.
```

Caveman skill installed via `.agents/skills/caveman`. Use `/caveman` to toggle intensity (lite/full/ultra).
