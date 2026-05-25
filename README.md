# E-Parking System v2

Automated parking management system with real-time hardware control, multi-payment support, and operator POS interface.

## Architecture

```
                    ┌─────────────────────────┐
                    │   Nuxt 3 SPA (Operator)  │
                    │   Element Plus + Pinia   │
                    └──────────┬──────────────┘
                               │ WebSocket (Redis Broadcaster)
                    ┌──────────▼──────────────┐
                    │   FastAPI (Gunicorn)     │
                    │   JWT Auth + Rate Limit  │
                    └────┬──────────┬─────────┘
                         │          │
               ┌─────────▼──┐  ┌────▼─────────┐
               │ PostgreSQL │  │   Redis 7     │
               │ pgBouncer  │  │ Streams/PubSub│
               └────────────┘  └────┬─────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              ┌─────▼─────┐ ┌──────▼──────┐ ┌──────▼──────┐
              │ Gate-In    │ │ Gate-Out    │ │ ARQ Workers │
              │ Daemon     │ │ Daemon      │ │ (Critical + │
              │ (state     │ │ (state      │ │  Bg tasks)  │
              │  machine)  │ │  machine)   │ │             │
              └─────┬──────┘ └──────┬──────┘ └─────────────┘
                    │               │
              ┌─────▼───────────────▼──────┐
              │  Hardware Protocols (stdlib)│
              │  Compass | ENET | Serial    │
              │  ESC/POS | PASSTI E-Money   │
              └────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (async), SQLAlchemy 2.0, Pydantic v2 |
| **Auth** | JWT (httpOnly cookies), bcrypt |
| **Frontend** | Nuxt 3 (SPA), Vue 3, Element Plus, Pinia |
| **Database** | PostgreSQL 16 + pgBouncer (transaction pooling) |
| **Cache / IPC** | Redis 7 (Streams ACK, Pub/Sub, Cache) |
| **Task Queue** | ARQ (Critical + Background workers with cron) |
| **Hardware** | Compass, ENET, PASSTI, ESC/POS, Serial RS-232 |
| **Observability** | structlog (JSON, trace_id), Prometheus metrics |
| **Containerization** | Docker Compose (dev + prod) |
| **Process Mgmt** | systemd (5 service units) |

## Quick Start

```bash
# 1. Clone and set up environment
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Start infrastructure (PostgreSQL, Redis, pgBouncer)
docker compose up -d

# 4. Run migrations and seed data
alembic upgrade head
python scripts/seed.py

# 5. Start API
uvicorn api.app.main:app --reload

# 6. Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Frontend runs at `http://localhost:3000`, API docs at `http://localhost:8000/docs`.

## Features

### Parking Flow
- **Gate Entry** — Cash ticket printing, RFID member, PASSTI E-Money balance check
- **Gate Exit** — Cash POS payment, RFID auto-complete, E-Money deduction
- **E-Money** — Multi-bank settlement files, transaction verification, correction mode

### Operator POS
- Real-time WebSocket events (vehicle detected, payment timeout, snapshot)
- Triple payment method buttons with keyboard shortcuts (F1/F2/F3)
- Cash payment modal with change calculation
- RTSP camera snapshot preview

### Admin Panel
- Transaction management (CRUD, ManualOpenLog, AbandonedVehicles)
- Device management (Cameras, Printers, POS, Gates, E-Money Readers)
- Member management (Members, Groups, Renewals)
- Reports (date-range, e-money breakdown)
- Settings (General, Vehicle Types, Users, Shifts, Areas)

### Hardware Daemons
- State machine-driven gate control (Redis Streams commands)
- ACK-based reliability with state persistence & recovery
- Heartbeat every 30s, graceful shutdown on SIGTERM/SIGINT
- Supports Compass, ENET, and Serial controller protocols

## Project Structure

```
parking-system-v2/
├── api/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py         # App factory & lifespan
│   │   ├── models/         # SQLAlchemy ORM (25 models)
│   │   ├── routes/         # API endpoints (19 modules)
│   │   ├── schemas/        # Pydantic request/response (18 modules)
│   │   ├── services/       # Business logic
│   │   ├── middleware/      # Auth, metrics, rate-limit, security
│   │   ├── websocket/      # WS handlers + Redis broadcaster
│   │   └── cache/          # Redis cache helpers
│   ├── alembic/            # DB migration scripts
│   └── tests/
├── frontend/               # Nuxt 3 SPA
│   ├── pages/              # Login, POS, gate-in, transaksi, admin
│   ├── components/         # ConfirmDialog, CrudModal, DataTable
│   ├── composables/        # useApi, useCrud
│   ├── stores/             # auth, gate, website (Pinia)
│   ├── plugins/            # WebSocket auto-reconnect
│   └── middleware/         # Auth route protection
├── daemons/                # Hardware gateway daemons
│   ├── base.py             # Abstract daemon (Redis Streams consumer)
│   ├── gate_in.py          # Gate-in state machine (10 states)
│   └── gate_out.py         # Gate-out state machine (5 states)
├── protocols/              # Hardware protocol implementations
│   ├── compass/            # Compass TCP controller
│   ├── enet/               # ENET controller
│   ├── passti/             # PASSTI E-Money reader
│   ├── escpos/             # ESC/POS printer
│   ├── serial/             # RS-232 serial controller
│   └── factory.py          # Transport factory
├── workers/                # ARQ job queues
│   ├── critical/           # print_worker, snapshot_worker
│   └── background/         # settlement, cleanup, notification
├── shared/                 # Cross-cutting modules
│   ├── config.py           # 80+ pydantic-settings
│   ├── redis.py            # Async Redis client (singleton)
│   ├── events.py           # Redis IPC message schemas
│   └── logging.py          # structlog + trace_id binding
├── services/               # Machine vision (ANPR, YOLOv8)
├── docker/                 # Dockerfiles & nginx config
├── systemd/                # systemd service units
├── scripts/                # Seed, deploy, benchmarks
└── tests/                  # E2E, smoke, load tests
```

## Testing

```bash
# Backend tests
pytest -x -q --tb=short

# Frontend tests
cd frontend && npm run test

# Load tests
locust -f tests/load/locustfile.py

# Lint & type check
ruff check .
mypy .
```

## Deployment

### Single Server

```bash
# Production Docker Compose
docker compose -f docker/docker-compose.prod.yml up -d

# Or with systemd
sudo systemctl start parking-api
sudo systemctl start parking-daemon-gate-in@GIN-01   # entry gates only; exit lanes use booth-bridge
sudo systemctl start parking-worker-critical
sudo systemctl start parking-worker-snapshot
sudo systemctl start parking-worker-bg
```

### Multi-PC (Server + Booths)

For installations with multiple gate-outs across separate booth PCs:

```bash
# See full guide for server + booth PC setup
cat docs/FIELD_TECH_GUIDE.md
```

**Quick reference:**
- **Server PC**: API, database, Redis, frontend, nginx
- **Booth PC(s)**: Booth bridge (serial devices) + Chrome POS

See `docs/` for full runbook, checklist, and training materials.

## Documentation

| Document | Description |
|----------|-------------|
| `docs/EParking_v2_Development_Plan.md` | Architecture, data models, design decisions |
| `docs/GATE_FLOW_SPEC.md` | Gate entry/exit flow specifications |
| `docs/FIELD_TECH_GUIDE.md` | Field install walkthrough (server + booth PCs, wizard) |
| `docs/DEVELOPMENT_TESTING_GUIDE.md` | Pre-deployment testing procedures |
| `docs/OPERATIONS_RUNBOOK.md` | Day-to-day operations guide |
| `docs/ONCALL_RUNBOOK.md` | On-call incident response |
| `docs/GO_LIVE_CHECKLIST.md` | Production go-live checklist |
| `docs/SECURITY_REVIEW.md` | Security audit documentation |

## License

MIT
