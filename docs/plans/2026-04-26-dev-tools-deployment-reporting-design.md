# E-Parking v2 — Dev Tools, Deployment & Reporting Enhancement

> **Date:** 26 April 2026
> **Version:** 1.0.0
> **Status:** Approved for implementation

---

## 1. Development Run/Stop Scripts

### 1.1 `scripts/dev-start.sh`

**Purpose:** One-command startup for local development with hardware testing.

**Steps:**
1. Start infrastructure: `docker compose up -d postgres redis pgbouncer`
2. Wait for PostgreSQL healthcheck (`pg_isready`)
3. Run Alembic migrations: `alembic upgrade head`
4. Seed DB if empty: `python scripts/seed.py --skip-if-seeded`
5. Start API server in background → log to `logs/api.log`
6. Start frontend dev server in background → log to `logs/frontend.log`
7. Start gate-in daemon for hardware testing → log to `logs/daemon-gate-in.log`
8. Start gate-out daemon → log to `logs/daemon-gate-out.log`
9. Print summary with all process PIDs and URLs

**Outputs:**
- PID files in `pids/` directory for clean shutdown
- Log files in `logs/` directory

### 1.2 `scripts/dev-stop.sh`

**Purpose:** One-command shutdown.

**Steps:**
1. Kill API, frontend, and daemon processes by PID files
2. Optionally stop Docker infrastructure (`--infra` flag)
3. Clean up PID files

### 1.3 `scripts/dev-tmux.sh` (Optional)

**Purpose:** All logs visible in one terminal window for hardware debugging.

**Layout:**
- Creates tmux session `eparking-dev` with 4 panes:
  - Pane 1: PostgreSQL + Redis logs (`docker compose logs -f`)
  - Pane 2: API logs
  - Pane 3: Frontend logs
  - Pane 4: Gate daemon logs
- Attach: `tmux attach -t eparking-dev`
- Stop: `tmux kill-session -t eparking-dev`

---

## 2. Desktop Shortcuts (.desktop Files)

### Files
- `~/.local/share/applications/eparking-start.desktop`
- `~/.local/share/applications/eparking-stop.desktop`
- `~/Desktop/E-Parking Start.desktop`
- `~/Desktop/E-Parking Stop.desktop`

### Behavior
- **Start:** Runs `scripts/dev-start.sh`, opens terminal showing progress, then opens browser to `http://localhost:3000`
- **Stop:** Runs `scripts/dev-stop.sh`, shows confirmation dialog
- **Icons:** Uses custom parking icons from `assets/icons/`

### Trust Setup
- Helper script `scripts/create-shortcuts.sh` marks `.desktop` files trusted automatically

---

## 3. System Tray Indicator

### Script: `scripts/tray-indicator.py`

**Dependencies:** `PyGObject` (GTK3) + `libappindicator3`

**Icon States:**
- 🟡 Gray = System not running
- 🟢 Green = All services running
- 🔴 Red = One or more services stopped/crashed

**Menu Items:**
- "Start E-Parking" → runs dev-start.sh
- "Stop E-Parking" → runs dev-stop.sh
- "Open POS" → opens browser to localhost:3000
- "View Logs" → opens file manager to `logs/` directory
- "View API Docs" → opens `http://localhost:8000/docs`
- "Exit" → quits indicator (does NOT stop services)

**Auto-refresh:**
- Polls every 5 seconds: checks API, frontend, Redis, PostgreSQL health
- Updates icon color accordingly

**Auto-start:**
- Can register itself in `~/.config/autostart/`

---

## 4. Hybrid Guided Installer (`scripts/install.sh`)

### Target: Fresh Ubuntu 24.04 Server
**Run as:** `sudo bash scripts/install.sh` (checks for root)

### Phase-by-Phase Flow

| Phase | Action | Prompt |
|-------|--------|--------|
| 1 | System check (Ubuntu 24.04, internet, disk space) | "Continue?" |
| 2 | Install packages (Python 3.12, PostgreSQL 16, Redis 7, nginx, Node.js 20, npm, git) | "Install packages?" |
| 3 | Create `parking` user, add to `dialout` | "Create user?" |
| 4 | Clone repo to `/opt/parking-system-v2`, create venv, pip install | "Set up app?" |
| 5 | Create DB user & database, run migrations | "Set up DB?" |
| 6 | Run seed script | "Seed data?" |
| 7 | Build frontend | "Build frontend?" |
| 8 | Copy systemd services, daemon-reload | "Install services?" |
| 9 | Interactive site config prompts (name, address, phone) | "Configure site?" |
| 10 | Interactive hardware config prompts (controller IPs, serial port) | "Configure hardware?" |
| 11 | Enable and start core services | "Start services?" |
| 12 | Health check via `curl http://localhost/api/health` | "Run health check?" |

### Site Config During Install
- Creates initial site settings via API:
  - `site_name`, `site_address`, `site_phone`, `site_email`
- Used in receipt headers and reports

### Hardware Config During Install
- Creates initial `GateIn`, `GateOut`, `EmoneyReader` records via API
- Operator can refine later in admin panel

### Post-Install
- Prints service status, URLs, default login credentials
- Saves config to `/opt/parking-system-v2/.install-config.json`

---

## 5. Site Configuration Enhancement

### Current Gap
- No dedicated model for site/location details
- Generic `Setting` key-value store only

### New Model: `SiteConfig`

```python
class SiteConfig(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "site_config"
    
    name: Mapped[str]          # "Parking Mall ABC"
    address: Mapped[str | None]
    city: Mapped[str | None]
    phone: Mapped[str | None]
    email: Mapped[str | None]
    tax_id: Mapped[str | None]  # NPWP
    logo_url: Mapped[str | None]
    
    # Singleton — only one row allowed
```

### New API: `/api/site-config`
- GET: Returns current site config
- PUT: Updates site config (admin only)

### Frontend
- New "Site Info" tab on Settings page (`frontend/pages/setting.vue`)
- Form fields: Name, Address, City, Phone, Email, Tax ID
- Preview of site name on receipt header

### Usage
- Receipt printer header
- Report footers
- Ticket printout header

---

## 6. Reporting Enhancements

### 6a. Shift Reports

**Endpoint:** `GET /api/reports/shift`
- Query params: `date_from`, `date_to`, `shift_id` (optional)
- Returns shift-wise breakdown per operator

**Fields:**
- shift_id, shift_name, date
- operator_id, operator_name
- total_transactions, total_revenue
- cash_revenue, emoney_revenue, rfid_revenue
- active_transactions, completed_transactions
- average_fee

**Frontend:** New "Per Shift" tab on Reports page

### 6b. Daily / Weekly / Monthly Presets

**Convenience Endpoints:**
- `GET /api/reports/summary/daily?date=YYYY-MM-DD`
- `GET /api/reports/summary/weekly?year=YYYY&week=WW`
- `GET /api/reports/summary/monthly?year=YYYY&month=MM`

**Frontend Quick Buttons:**
- "Hari Ini" (Today)
- "Minggu Ini" (This Week)
- "Bulan Ini" (This Month)
- "Bulan Lalu" (Last Month)

### 6c. Report Export (CSV + Excel + PDF)

**Endpoints:**
- `GET /api/reports/{type}/export?format=csv|xlsx|pdf&date_from=...&date_to=...`

**Formats:**
- **CSV:** Python `csv` module (stdlib)
- **Excel:** `openpyxl` — formatted headers, auto-width, currency format
- **PDF:** `reportlab` — table layout with site header, date range, summary stats

**Frontend:** Export buttons on each report tab

**File naming:** `EParking_Report_{type}_{date_from}_{date_to}.{ext}`

---

## Deliverables Summary

| # | Deliverable | Files |
|---|-------------|-------|
| 1 | Dev start script | `scripts/dev-start.sh` |
| 2 | Dev stop script | `scripts/dev-stop.sh` |
| 3 | Dev tmux variant | `scripts/dev-tmux.sh` |
| 4 | Desktop shortcuts | `scripts/create-shortcuts.sh`, `.desktop` files |
| 5 | System tray indicator | `scripts/tray-indicator.py` |
| 6 | Hybrid installer | `scripts/install.sh` |
| 7 | Site config model | `api/app/models/site_config.py` |
| 8 | Site config API | `api/app/routes/site_config.py` |
| 9 | Site config UI | Update `frontend/pages/setting.vue` |
| 10 | Shift report API | Update `api/app/routes/reports.py` |
| 11 | Report presets API | Update `api/app/routes/reports.py` |
| 12 | Report export API | `api/app/services/report_export.py` + routes |
| 13 | Report UI enhancements | Update `frontend/pages/report.vue` |
| 14 | Alembic migration | `api/alembic/versions/` |

---

*Approved for implementation on 26 April 2026.*
