# E-Parking System v2

> **Stack:** FastAPI + SQLAlchemy async + Nuxt 3 + PostgreSQL + Redis + ARQ

## Quick Start

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Start infrastructure
docker compose up -d

# 4. Run migrations
alembic upgrade head

# 5. Seed data
python scripts/seed.py

# 6. Start API
uvicorn api.app.main:app --reload
```

## Development

See `docs/EParking_v2_Development_Plan.md` for full architecture and timeline.

## License

MIT
