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
                                                         Transaction created
Vehicle exits  → Controller (IN1 sensor) → GateOutDaemon → Redis Pub/Sub → API
                                                              ↓
                                                         POS notified (WebSocket)
                                                              ↓
                                               Operator pays (Cash/RFID/E-Money)
                                                              ↓
                                                         Gate opens via Redis Stream
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
- Heartbeat every 30 seconds

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
| `daemons/cli.py` | Daemon runner — reads gate config from DB |
| `daemons/base.py` | BaseDaemon — Redis Streams consumer + Pub/Sub publisher |
| `api/app/main.py` | FastAPI app factory — where routers are registered |
| `frontend/nuxt.config.ts` | Frontend config — `apiBaseUrl`, modules |
| `frontend/stores/website.js` | Gate cache — fetches `/api/gates?direction=IN/OUT` |
| `shared/config.py` | Settings — loaded from `.env` via pydantic-settings |
| `api/alembic/versions/` | All DB migrations — read these before schema changes |
| `api/app/middleware/api_key.py` | API key auth for booth bridge → machine-to-machine |
| `api/app/routes/payments.py` | Payment routes including `/emoney/booth-result` |
| `api/app/services/event_consumer.py` | Server-side Redis Pub/Sub event consumer |
| `booth_bridge/websocket_server.py` | PASSTI parsing + direct API calls |
| `shared/events.py` | All Redis IPC event/command models |

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
- **Hardware guide:** `docs/BOOTH_DEPLOYMENT.md`

---

*Last updated: April 29, 2026*
*Version: 2.2.0*
