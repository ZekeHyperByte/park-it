# E-Parking v2 — Dev Tools, Deployment & Reporting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create development scripts, desktop shortcuts, system tray indicator, hybrid installer, site config model, and enhanced reporting (shift, presets, CSV/Excel/PDF export).

**Architecture:** Shell scripts for dev environment management; Python GTK app for system tray; bash installer with confirmation prompts; FastAPI model/route/UI additions for site config and reporting enhancements.

**Tech Stack:** Bash, Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, Element Plus, Vue 3, openpyxl, reportlab

---

## Task 1: Create Dev Start Script

**Files:**
- Create: `scripts/dev-start.sh`
- Create: `logs/.gitkeep`
- Create: `pids/.gitkeep`

**Step 1: Create logs and pids directories**

```bash
mkdir -p logs pids
touch logs/.gitkeep pids/.gitkeep
```

**Step 2: Write dev-start.sh**

```bash
#!/bin/bash
set -euo pipefail

# E-Parking v2 Development Start Script
# Usage: ./scripts/dev-start.sh [--with-tmux]

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="$PROJECT_ROOT/logs"
PIDS_DIR="$PROJECT_ROOT/pids"
INFRA_ONLY=false

if [[ "${1:-}" == "--infra-only" ]]; then
    INFRA_ONLY=true
fi

echo "=== E-Parking v2 Development Start ==="

# 1. Start infrastructure
echo "[1/5] Starting PostgreSQL, Redis, pgBouncer..."
cd "$PROJECT_ROOT"
docker compose up -d postgres redis pgbouncer

# Wait for PostgreSQL
echo "[2/5] Waiting for PostgreSQL..."
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U parking -d parking >/dev/null 2>&1; then
        echo "  PostgreSQL is ready!"
        break
    fi
    sleep 1
done

# 3. Run migrations
echo "[3/5] Running database migrations..."
source .venv/bin/activate
alembic upgrade head

# 4. Seed if needed
echo "[4/5] Seeding development data (if needed)..."
python scripts/seed.py

if $INFRA_ONLY; then
    echo "=== Infrastructure ready ==="
    echo "  PostgreSQL: localhost:5432"
    echo "  pgBouncer:  localhost:6432"
    echo "  Redis:      localhost:6379"
    exit 0
fi

# 5. Start API
echo "[5/5] Starting services..."

# API
if [[ -f "$PIDS_DIR/api.pid" ]] && kill -0 "$(cat "$PIDS_DIR/api.pid")" 2>/dev/null; then
    echo "  API already running (PID $(cat "$PIDS_DIR/api.pid"))"
else
    nohup .venv/bin/uvicorn api.app.main:app --reload --host 0.0.0.0 --port 8000 > "$LOGS_DIR/api.log" 2>&1 &
    echo $! > "$PIDS_DIR/api.pid"
    echo "  API started (PID $!) → http://localhost:8000"
fi

# Frontend
if [[ -f "$PIDS_DIR/frontend.pid" ]] && kill -0 "$(cat "$PIDS_DIR/frontend.pid")" 2>/dev/null; then
    echo "  Frontend already running (PID $(cat "$PIDS_DIR/frontend.pid"))"
else
    cd "$PROJECT_ROOT/frontend"
    nohup npm run dev > "$LOGS_DIR/frontend.log" 2>&1 &
    echo $! > "$PIDS_DIR/frontend.pid"
    echo "  Frontend started (PID $!) → http://localhost:3000"
fi

echo ""
echo "=== All services started ==="
echo "  API:      http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "  Logs:     $LOGS_DIR/"
echo "  PIDs:     $PIDS_DIR/"
echo ""
echo "  To stop:  ./scripts/dev-stop.sh"
```

**Step 3: Make executable**

```bash
chmod +x scripts/dev-start.sh
```

**Step 4: Test**

```bash
./scripts/dev-start.sh --infra-only
```

Expected: Docker containers start, migrations run, script exits.

**Step 5: Commit**

```bash
git add scripts/dev-start.sh logs/.gitkeep pids/.gitkeep
git commit -m "feat(dev): add dev-start.sh for one-command development startup"
```

---

## Task 2: Create Dev Stop Script

**Files:**
- Create: `scripts/dev-stop.sh`

**Step 1: Write dev-stop.sh**

```bash
#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDS_DIR="$PROJECT_ROOT/pids"
STOP_INFRA=false

if [[ "${1:-}" == "--infra" ]]; then
    STOP_INFRA=true
fi

echo "=== E-Parking v2 Development Stop ==="

# Stop services by PID
for service in api frontend; do
    pid_file="$PIDS_DIR/$service.pid"
    if [[ -f "$pid_file" ]]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Stopping $service (PID $pid)..."
            kill "$pid" || true
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                echo "  Force killing $service..."
                kill -9 "$pid" || true
            fi
        fi
        rm -f "$pid_file"
    fi
done

# Stop daemons if any
for pid_file in "$PIDS_DIR"/daemon-*.pid; do
    [[ -f "$pid_file" ]] || continue
    pid=$(cat "$pid_file")
    service=$(basename "$pid_file" .pid)
    if kill -0 "$pid" 2>/dev/null; then
        echo "  Stopping $service (PID $pid)..."
        kill "$pid" || true
    fi
    rm -f "$pid_file"
done

if $STOP_INFRA; then
    echo "  Stopping Docker infrastructure..."
    cd "$PROJECT_ROOT"
    docker compose down
fi

echo "=== Development environment stopped ==="
```

**Step 2: Make executable and test**

```bash
chmod +x scripts/dev-stop.sh
./scripts/dev-stop.sh
```

Expected: "Development environment stopped" (even if nothing was running).

**Step 3: Commit**

```bash
git add scripts/dev-stop.sh
git commit -m "feat(dev): add dev-stop.sh for one-command development shutdown"
```

---

## Task 3: Create Dev Tmux Script

**Files:**
- Create: `scripts/dev-tmux.sh`

**Step 1: Write dev-tmux.sh**

```bash
#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="eparking-dev"

echo "=== E-Parking v2 tmux Development Session ==="

# Check if tmux is installed
if ! command -v tmux &>/dev/null; then
    echo "ERROR: tmux is not installed. Install with: sudo apt install tmux"
    exit 1
fi

# Kill existing session if any
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Start infrastructure first
cd "$PROJECT_ROOT"
docker compose up -d postgres redis pgbouncer

# Create new session
tmux new-session -d -s "$SESSION" -n "infra"

# Pane 1: Infrastructure logs
tmux send-keys -t "$SESSION:infra" "cd $PROJECT_ROOT && docker compose logs -f" C-m

# Pane 2: API
tmux split-window -h -t "$SESSION:infra"
tmux send-keys -t "$SESSION:infra.1" "cd $PROJECT_ROOT && source .venv/bin/activate && alembic upgrade head && uvicorn api.app.main:app --reload --host 0.0.0.0 --port 8000" C-m

# Pane 3: Frontend
tmux split-window -v -t "$SESSION:infra.0"
tmux send-keys -t "$SESSION:infra.2" "cd $PROJECT_ROOT/frontend && npm run dev" C-m

# Pane 4: Daemon logs placeholder
tmux split-window -v -t "$SESSION:infra.1"
tmux send-keys -t "$SESSION:infra.3" "cd $PROJECT_ROOT && echo 'Run gate daemons here if needed' && bash" C-m

# Select layout
tmux select-layout -t "$SESSION:infra" tiled

# Attach
echo "Attaching to tmux session '$SESSION'..."
echo "  Detach with: Ctrl+B then D"
echo "  Kill with:   tmux kill-session -t $SESSION"
tmux attach -t "$SESSION"
```

**Step 2: Make executable**

```bash
chmod +x scripts/dev-tmux.sh
```

**Step 3: Commit**

```bash
git add scripts/dev-tmux.sh
git commit -m "feat(dev): add dev-tmux.sh for tmux-based dev environment"
```

---

## Task 4: Create Desktop Shortcuts

**Files:**
- Create: `scripts/create-shortcuts.sh`
- Create: `assets/icons/eparking-start.svg`
- Create: `assets/icons/eparking-stop.svg`

**Step 1: Create icon directory**

```bash
mkdir -p assets/icons
```

**Step 2: Create simple SVG icons**

For `assets/icons/eparking-start.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="#10b981">
  <rect x="4" y="20" width="56" height="28" rx="4"/>
  <circle cx="16" cy="48" r="6" fill="#374151"/>
  <circle cx="48" cy="48" r="6" fill="#374151"/>
  <rect x="8" y="24" width="16" height="10" rx="2" fill="#d1fae5"/>
  <text x="32" y="18" text-anchor="middle" font-size="10" fill="#10b981">START</text>
</svg>
```

For `assets/icons/eparking-stop.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="#ef4444">
  <rect x="4" y="20" width="56" height="28" rx="4"/>
  <circle cx="16" cy="48" r="6" fill="#374151"/>
  <circle cx="48" cy="48" r="6" fill="#374151"/>
  <rect x="8" y="24" width="16" height="10" rx="2" fill="#fee2e2"/>
  <text x="32" y="18" text-anchor="middle" font-size="10" fill="#ef4444">STOP</text>
</svg>
```

**Step 3: Write create-shortcuts.sh**

```bash
#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_DESKTOP="$HOME/Desktop"
APPLICATIONS_DIR="$HOME/.local/share/applications"
ICON_DIR="$PROJECT_ROOT/assets/icons"

mkdir -p "$APPLICATIONS_DIR"

echo "=== Creating E-Parking Desktop Shortcuts ==="

# Create .desktop files
cat > "$APPLICATIONS_DIR/eparking-start.desktop" <<EOF
[Desktop Entry]
Name=E-Parking Start
Comment=Start E-Parking development environment
Exec=bash -c 'cd $PROJECT_ROOT && ./scripts/dev-start.sh && xdg-open http://localhost:3000'
Icon=$ICON_DIR/eparking-start.svg
Terminal=true
Type=Application
Categories=Development;
EOF

cat > "$APPLICATIONS_DIR/eparking-stop.desktop" <<EOF
[Desktop Entry]
Name=E-Parking Stop
Comment=Stop E-Parking development environment
Exec=$PROJECT_ROOT/scripts/dev-stop.sh
Icon=$ICON_DIR/eparking-stop.svg
Terminal=true
Type=Application
Categories=Development;
EOF

# Copy to Desktop
cp "$APPLICATIONS_DIR/eparking-start.desktop" "$USER_DESKTOP/"
cp "$APPLICATIONS_DIR/eparking-stop.desktop" "$USER_DESKTOP/"

# Mark as trusted (skip confirmation prompt)
chmod +x "$APPLICATIONS_DIR/eparking-start.desktop"
chmod +x "$APPLICATIONS_DIR/eparking-stop.desktop"
chmod +x "$USER_DESKTOP/eparking-start.desktop"
chmod +x "$USER_DESKTOP/eparking-stop.desktop"

echo "  Created: $USER_DESKTOP/E-Parking Start.desktop"
echo "  Created: $USER_DESKTOP/E-Parking Stop.desktop"
echo "  Done!"
```

**Step 4: Make executable and test**

```bash
chmod +x scripts/create-shortcuts.sh
./scripts/create-shortcuts.sh
```

Expected: Two `.desktop` files appear on Desktop.

**Step 5: Commit**

```bash
git add scripts/create-shortcuts.sh assets/icons/
git commit -m "feat(dev): add desktop shortcut creation script with icons"
```

---

## Task 5: Create System Tray Indicator

**Files:**
- Create: `scripts/tray-indicator.py`
- Create: `scripts/tray-indicator-requirements.txt`

**Step 1: Create requirements file**

```
PyGObject>=3.44.0
```

**Step 2: Write tray-indicator.py**

```python
#!/usr/bin/env python3
"""E-Parking v2 System Tray Indicator.

Shows a tray icon indicating system status with menu to start/stop/open.

Install deps:
    sudo apt install libappindicator3-1 gir1.2-appindicator3-0.1
    pip install -r scripts/tray-indicator-requirements.txt

Run:
    python scripts/tray-indicator.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")

from gi.repository import AppIndicator3, GLib, Gtk

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
LOGS_DIR = PROJECT_ROOT / "logs"
PIDS_DIR = PROJECT_ROOT / "pids"


def check_service(url: str, timeout: float = 2.0) -> bool:
    """Check if a service is responding."""
    import urllib.request

    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def get_status() -> dict:
    """Check status of all services."""
    return {
        "api": check_service("http://localhost:8000/api/health"),
        "frontend": check_service("http://localhost:3000"),
        "postgres": subprocess.call(
            ["docker", "compose", "exec", "-T", "postgres", "pg_isready", "-U", "parking"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        == 0,
        "redis": subprocess.call(
            ["docker", "compose", "exec", "-T", "redis", "redis-cli", "ping"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        == 0,
    }


def get_icon_name(status: dict) -> str:
    """Determine icon based on status."""
    if all(status.values()):
        return "emblem-default"  # Green check
    elif any(status.values()):
        return "dialog-warning"  # Yellow warning
    else:
        return "dialog-error"  # Red error


class TrayIndicator:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "eparking-tray",
            "dialog-error",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())
        self.update_status()

        # Poll every 5 seconds
        GLib.timeout_add_seconds(5, self.update_status)

    def build_menu(self):
        menu = Gtk.Menu()

        # Status label
        self.status_item = Gtk.MenuItem(label="Status: Checking...")
        self.status_item.set_sensitive(False)
        menu.append(self.status_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Actions
        start_item = Gtk.MenuItem(label="Start E-Parking")
        start_item.connect("activate", self.on_start)
        menu.append(start_item)

        stop_item = Gtk.MenuItem(label="Stop E-Parking")
        stop_item.connect("activate", self.on_stop)
        menu.append(stop_item)

        menu.append(Gtk.SeparatorMenuItem())

        open_pos_item = Gtk.MenuItem(label="Open POS")
        open_pos_item.connect("activate", self.on_open_pos)
        menu.append(open_pos_item)

        view_logs_item = Gtk.MenuItem(label="View Logs")
        view_logs_item.connect("activate", self.on_view_logs)
        menu.append(view_logs_item)

        view_docs_item = Gtk.MenuItem(label="View API Docs")
        view_docs_item.connect("activate", self.on_view_docs)
        menu.append(view_docs_item)

        menu.append(Gtk.SeparatorMenuItem())

        exit_item = Gtk.MenuItem(label="Exit")
        exit_item.connect("activate", self.on_exit)
        menu.append(exit_item)

        menu.show_all()
        return menu

    def update_status(self):
        status = get_status()
        icon = get_icon_name(status)
        self.indicator.set_icon_full(icon, "E-Parking Status")

        running = [k for k, v in status.items() if v]
        if len(running) == 4:
            label = "Status: All systems running"
        elif running:
            label = f"Status: {', '.join(running)} running"
        else:
            label = "Status: Stopped"
        self.status_item.set_label(label)

        return True  # Continue polling

    def on_start(self, _):
        subprocess.Popen(
            ["x-terminal-emulator", "-e", f"{PROJECT_ROOT}/scripts/dev-start.sh"],
            cwd=PROJECT_ROOT,
        )

    def on_stop(self, _):
        subprocess.Popen(
            ["x-terminal-emulator", "-e", f"{PROJECT_ROOT}/scripts/dev-stop.sh"],
            cwd=PROJECT_ROOT,
        )

    def on_open_pos(self, _):
        subprocess.Popen(["xdg-open", "http://localhost:3000"])

    def on_view_logs(self, _):
        subprocess.Popen(["xdg-open", str(LOGS_DIR)])

    def on_view_docs(self, _):
        subprocess.Popen(["xdg-open", "http://localhost:8000/docs"])

    def on_exit(self, _):
        Gtk.main_quit()


def main():
    indicator = TrayIndicator()
    Gtk.main()


if __name__ == "__main__":
    main()
```

**Step 3: Make executable**

```bash
chmod +x scripts/tray-indicator.py
```

**Step 4: Commit**

```bash
git add scripts/tray-indicator.py scripts/tray-indicator-requirements.txt
git commit -m "feat(dev): add system tray indicator for development environment"
```

---

## Task 6: Create Hybrid Guided Installer

**Files:**
- Create: `scripts/install.sh`

**Step 1: Write install.sh**

```bash
#!/bin/bash
set -euo pipefail

# E-Parking v2 Hybrid Guided Installer
# Target: Fresh Ubuntu 24.04 Server
# Usage: sudo bash scripts/install.sh

APP_NAME="E-Parking v2"
APP_DIR="/opt/parking-system-v2"
USER="parking"

colors() {
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
}
colors

prompt() {
    local msg="$1"
    read -rp "${msg} [Y/n]: " ans
    [[ -z "$ans" || "$ans" =~ ^[Yy]$ ]]
}

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo "========================================"
echo "  $APP_NAME - Guided Installer"
echo "========================================"
echo ""

# Phase 1: System Check
echo -e "${BLUE}Phase 1: System Check${NC}"
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}ERROR: Must run as root (use sudo)${NC}"
    exit 1
fi

if ! grep -q "Ubuntu 24.04" /etc/os-release 2>/dev/null; then
    log_warn "Not Ubuntu 24.04 — proceed with caution"
fi

log_info "Disk space: $(df -h / | awk 'NR==2{print $4}') available"
log_info "Memory: $(free -h | awk '/^Mem:/ {print $2}') total"

if ! prompt "Continue with installation?"; then
    echo "Aborted."
    exit 0
fi

# Phase 2: Install Packages
if prompt "Install system packages (PostgreSQL 16, Redis 7, nginx, Node.js 20)?"; then
    log_info "Updating apt..."
    apt-get update -qq
    
    log_info "Installing packages..."
    apt-get install -y -qq \
        postgresql-16 postgresql-contrib-16 \
        redis-server nginx \
        python3.12 python3.12-venv python3-pip \
        git curl wget \
        libpq-dev python3-dev
    
    # Node.js 20
    if ! command -v node &>/dev/null || [[ "$(node -v)" != v20* ]]; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt-get install -y -qq nodejs
    fi
    
    log_ok "Packages installed"
fi

# Phase 3: Create User
if prompt "Create '$USER' user?"; then
    if id "$USER" &>/dev/null; then
        log_warn "User '$USER' already exists"
    else
        useradd -r -s /bin/false "$USER"
        usermod -aG dialout "$USER"
        log_ok "User '$USER' created"
    fi
fi

# Phase 4: Setup Application
if prompt "Set up application in $APP_DIR?"; then
    if [[ -d "$APP_DIR" ]]; then
        log_warn "Directory exists — will update"
    else
        mkdir -p "$APP_DIR"
    fi
    
    # If running from repo, copy current code
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    if [[ -f "$SCRIPT_DIR/pyproject.toml" ]]; then
        log_info "Copying from current directory..."
        rsync -av --exclude='.git' --exclude='node_modules' --exclude='.venv' \
            "$SCRIPT_DIR/" "$APP_DIR/"
    else
        log_info "Cloning from git..."
        git clone <REPO_URL> "$APP_DIR"
    fi
    
    chown -R "$USER:$USER" "$APP_DIR"
    
    # Create venv
    sudo -u "$USER" python3.12 -m venv "$APP_DIR/.venv"
    sudo -u "$USER" "$APP_DIR/.venv/bin/pip" install -q -e "$APP_DIR/[dev]"
    
    log_ok "Application set up"
fi

# Phase 5: Database Setup
if prompt "Set up PostgreSQL database?"; then
    sudo -u postgres psql -c "CREATE USER parking WITH PASSWORD 'parking_secret';" 2>/dev/null || log_warn "User may already exist"
    sudo -u postgres psql -c "CREATE DATABASE parking OWNER parking;" 2>/dev/null || log_warn "Database may already exist"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE parking TO parking;"
    
    # Update pg_hba for local trust
    sudo -u postgres psql -c "ALTER USER parking WITH PASSWORD 'parking_secret';"
    
    cd "$APP_DIR"
    sudo -u "$USER" "$APP_DIR/.venv/bin/alembic" upgrade head
    
    log_ok "Database ready"
fi

# Phase 6: Seed Data
if prompt "Seed initial data?"; then
    cd "$APP_DIR"
    sudo -u "$USER" "$APP_DIR/.venv/bin/python" scripts/seed.py
    log_ok "Data seeded"
fi

# Phase 7: Build Frontend
if prompt "Build frontend?"; then
    cd "$APP_DIR/frontend"
    npm install -s
    npm run build
    log_ok "Frontend built"
fi

# Phase 8: Systemd Services
if prompt "Install systemd services?"; then
    cp "$APP_DIR/systemd/"*.service /etc/systemd/system/
    systemctl daemon-reload
    log_ok "Services installed"
fi

# Phase 9: Site Config
if prompt "Configure site information?"; then
    read -rp "Parking site name: " site_name
    read -rp "Address: " site_address
    read -rp "City: " site_city
    read -rp "Phone: " site_phone
    read -rp "Email: " site_email
    
    # Save to settings via API later, or .env for now
    cat >> "$APP_DIR/.env" <<EOF

# Site Configuration
SITE_NAME=${site_name}
SITE_ADDRESS=${site_address}
SITE_CITY=${site_city}
SITE_PHONE=${site_phone}
SITE_EMAIL=${site_email}
EOF
    
    log_ok "Site config saved"
fi

# Phase 10: Hardware Config
if prompt "Configure hardware?"; then
    read -rp "Gate-In controller IP [192.168.1.101]: " gin_ip
    gin_ip=${gin_ip:-192.168.1.101}
    read -rp "Gate-Out controller IP [192.168.1.102]: " gout_ip
    gout_ip=${gout_ip:-192.168.1.102}
    read -rp "E-Money reader serial port [/dev/ttyUSB0]: " emoney_port
    emoney_port=${emoney_port:-/dev/ttyUSB0}
    
    cat >> "$APP_DIR/.env" <<EOF

# Hardware Configuration
GATE_IN_HOST=${gin_ip}
GATE_OUT_HOST=${gout_ip}
EMONEY_SERIAL_PORT=${emoney_port}
EOF
    
    log_ok "Hardware config saved"
fi

# Phase 11: Start Services
if prompt "Start core services?"; then
    systemctl enable --now parking-api parking-worker-critical parking-worker-bg
    log_ok "Services started"
fi

# Phase 12: Health Check
if prompt "Run health check?"; then
    sleep 3
    if curl -sf http://localhost/api/health >/dev/null 2>&1; then
        log_ok "API is healthy!"
    else
        log_warn "API health check failed — check logs with: journalctl -u parking-api -f"
    fi
fi

# Save install config
cat > "$APP_DIR/.install-config.json" <<EOF
{
  "installed_at": "$(date -Iseconds)",
  "version": "2.0.0",
  "app_dir": "$APP_DIR",
  "user": "$USER"
}
EOF

echo ""
echo "========================================"
echo "  $APP_NAME Installation Complete!"
echo "========================================"
echo ""
echo "  API:       http://localhost/api"
echo "  Frontend:  http://localhost"
echo "  API Docs:  http://localhost/api/docs"
echo ""
echo "  Login:     admin / admin123"
echo "             operator / operator123"
echo ""
echo "  Logs:      journalctl -u parking-api -f"
echo "  Config:    $APP_DIR/.env"
echo ""
```

**Step 2: Make executable**

```bash
chmod +x scripts/install.sh
```

**Step 3: Commit**

```bash
git add scripts/install.sh
git commit -m "feat(deploy): add hybrid guided installer for Ubuntu 24.04"
```

---

## Task 7: Create Site Config Model + Migration

**Files:**
- Create: `api/app/models/site_config.py`
- Create: `api/alembic/versions/20260426_add_site_config.py`
- Modify: `api/app/models/__init__.py`

**Step 1: Write model**

```python
"""Site configuration model — singleton for parking location details."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class SiteConfig(Base, IntPKMixin, TimestampMixin):
    """Singleton site configuration.
    
    Only one row should exist in this table. Used for receipts,
    reports, and ticket headers.
    """

    __tablename__ = "site_config"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<SiteConfig(name={self.name}, city={self.city})>"
```

**Step 2: Add to models __init__.py**

Add import line:
```python
from api.app.models.site_config import SiteConfig
```

**Step 3: Create Alembic migration**

```bash
cd api && alembic revision -m "add site_config table"
```

Edit generated migration:
```python
"""add site_config table

Revision ID: <generated>
Revises: <parent>
Create Date: 2026-04-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '<generated>'
down_revision: Union[str, None] = '<parent>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'site_config',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('tax_id', sa.String(length=50), nullable=True),
        sa.Column('logo_url', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('site_config')
```

**Step 4: Run migration**

```bash
cd api && alembic upgrade head
```

Expected: Migration applies successfully.

**Step 5: Commit**

```bash
git add api/app/models/site_config.py api/app/models/__init__.py api/alembic/versions/
git commit -m "feat(site): add SiteConfig model and migration"
```

---

## Task 8: Create Site Config API Routes

**Files:**
- Create: `api/app/routes/site_config.py`
- Create: `api/app/schemas/site_config.py`
- Modify: `api/app/main.py` (include router)

**Step 1: Create schema**

```python
"""SiteConfig Pydantic schemas."""

from pydantic import BaseModel, ConfigDict


class SiteConfigBase(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None
    logo_url: str | None = None


class SiteConfigResponse(SiteConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class SiteConfigUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None
    logo_url: str | None = None
```

**Step 2: Create routes**

```python
"""Site configuration routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.site_config import SiteConfig
from api.app.schemas.common import SuccessResponse
from api.app.schemas.site_config import SiteConfigResponse, SiteConfigUpdate
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("site_config_routes")

router = APIRouter(prefix="/site-config", tags=["Site Config"])


@router.get("", response_model=SiteConfigResponse)
async def get_site_config(
    db: AsyncSession = Depends(get_db),
) -> SiteConfigResponse:
    """Get site configuration (singleton)."""
    result = await db.execute(select(SiteConfig))
    config = result.scalar_one_or_none()
    
    if config is None:
        # Return default if not set
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site config not set",
        )
    
    return SiteConfigResponse.model_validate(config)


@router.put("", response_model=SiteConfigResponse)
async def update_site_config(
    data: SiteConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SiteConfigResponse:
    """Update site configuration (create if not exists)."""
    result = await db.execute(select(SiteConfig))
    config = result.scalar_one_or_none()
    
    if config is None:
        # Create with defaults for required fields
        create_data = data.model_dump(exclude_unset=True)
        if "name" not in create_data or create_data["name"] is None:
            create_data["name"] = "E-Parking"
        config = SiteConfig(**create_data)
        db.add(config)
    else:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
    
    await db.commit()
    await db.refresh(config)
    logger.info("site_config_updated")
    return SiteConfigResponse.model_validate(config)
```

**Step 3: Include router in main.py**

Add import:
```python
from api.app.routes import site_config as site_config_router
```

Add router registration (around line where other routers are included):
```python
app.include_router(site_config_router.router)
```

**Step 4: Test**

```bash
curl http://localhost:8000/api/site-config
```

Expected: 404 (not set yet)

```bash
curl -X PUT http://localhost:8000/api/site-config \
  -H "Content-Type: application/json" \
  -d '{"name":"Parking Mall ABC","address":"Jl. Sudirman No.1","city":"Jakarta"}'
```

Expected: SiteConfig JSON response.

**Step 5: Commit**

```bash
git add api/app/routes/site_config.py api/app/schemas/site_config.py api/app/main.py
git commit -m "feat(site): add SiteConfig API routes and schemas"
```

---

## Task 9: Add Site Config UI to Settings Page

**Files:**
- Modify: `frontend/pages/setting.vue`

**Step 1: Add new tab "Site Info"**

Add tab pane after "General Settings" tab:

```vue
<!-- Site Info -->
<el-tab-pane label="Site Info" name="site-info">
  <el-form :model="siteConfig" label-width="120px">
    <el-form-item label="Site Name">
      <el-input v-model="siteConfig.name" placeholder="Parking Mall ABC" />
    </el-form-item>
    <el-form-item label="Address">
      <el-input v-model="siteConfig.address" type="textarea" rows="2" />
    </el-form-item>
    <el-form-item label="City">
      <el-input v-model="siteConfig.city" />
    </el-form-item>
    <el-form-item label="Phone">
      <el-input v-model="siteConfig.phone" />
    </el-form-item>
    <el-form-item label="Email">
      <el-input v-model="siteConfig.email" />
    </el-form-item>
    <el-form-item label="Tax ID (NPWP)">
      <el-input v-model="siteConfig.tax_id" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="saveSiteConfig">Save</el-button>
    </el-form-item>
  </el-form>
  
  <el-divider />
  
  <h4>Receipt Preview</h4>
  <el-card class="receipt-preview">
    <div class="text-center">
      <h3>{{ siteConfig.name || 'E-Parking' }}</h3>
      <p class="text-small">{{ siteConfig.address }}</p>
      <p class="text-small">{{ siteConfig.city }} | {{ siteConfig.phone }}</p>
    </div>
  </el-card>
</el-tab-pane>
```

**Step 2: Add script methods**

In `<script setup>` or `<script>` section, add:

```javascript
const siteConfig = ref({
  name: '',
  address: '',
  city: '',
  phone: '',
  email: '',
  tax_id: '',
})

async function loadSiteConfig() {
  try {
    const { data } = await $api.get('/site-config')
    siteConfig.value = data
  } catch (e) {
    if (e.response?.status !== 404) {
      console.error('Failed to load site config', e)
    }
  }
}

async function saveSiteConfig() {
  try {
    await $api.put('/site-config', siteConfig.value)
    ElMessage.success('Site config saved')
  } catch (e) {
    ElMessage.error('Failed to save site config')
  }
}

onMounted(() => {
  loadSiteConfig()
})
```

**Step 3: Test**
- Open Settings page → "Site Info" tab
- Fill in fields → Save
- Verify receipt preview updates

**Step 4: Commit**

```bash
git add frontend/pages/setting.vue
git commit -m "feat(site): add Site Info tab to settings page"
```

---

## Task 10: Add Shift Report Endpoint

**Files:**
- Modify: `api/app/routes/reports.py`
- Modify: `api/app/schemas/report.py`

**Step 1: Add ShiftReport schema**

```python
class ShiftReportItem(BaseModel):
    shift_id: int
    shift_name: str
    date: date
    operator_id: int | None
    operator_name: str | None
    total_transactions: int
    total_revenue: int
    cash_revenue: int
    emoney_revenue: int
    rfid_revenue: int
    active_transactions: int
    completed_transactions: int
    average_fee: float


class ShiftReport(BaseModel):
    items: list[ShiftReportItem]
    total_revenue: int
    total_transactions: int
```

**Step 2: Add shift report route**

```python
@router.get("/shift", response_model=ShiftReport)
async def get_shift_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    shift_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> ShiftReport:
    """Get parking shift report for date range."""
    from api.app.models.shift import Shift
    from api.app.models.user import User
    from api.app.models.parking_transaction import ParkingTransaction
    
    # Base query
    query = select(
        Shift.id.label("shift_id"),
        Shift.name.label("shift_name"),
        func.date(ParkingTransaction.entry_time).label("date"),
        ParkingTransaction.operator_id,
        User.full_name.label("operator_name"),
        func.count(ParkingTransaction.id).label("total_transactions"),
        func.sum(ParkingTransaction.fee).label("total_revenue"),
        func.sum(
            func.case((ParkingTransaction.payment_method == "CASH", ParkingTransaction.fee), else_=0)
        ).label("cash_revenue"),
        func.sum(
            func.case((ParkingTransaction.payment_method == "EMONEY", ParkingTransaction.fee), else_=0)
        ).label("emoney_revenue"),
        func.sum(
            func.case((ParkingTransaction.payment_method == "RFID_MEMBER", ParkingTransaction.fee), else_=0)
        ).label("rfid_revenue"),
        func.sum(
            func.case((ParkingTransaction.status == "ACTIVE", 1), else_=0)
        ).label("active_transactions"),
        func.sum(
            func.case((ParkingTransaction.status == "COMPLETED", 1), else_=0)
        ).label("completed_transactions"),
    ).select_from(Shift).join(
        ParkingTransaction, ParkingTransaction.shift_id == Shift.id
    ).outerjoin(
        User, User.id == ParkingTransaction.operator_id
    ).where(
        func.date(ParkingTransaction.entry_time) >= date_from,
        func.date(ParkingTransaction.entry_time) < date_to,
    ).group_by(
        Shift.id, Shift.name, func.date(ParkingTransaction.entry_time),
        ParkingTransaction.operator_id, User.full_name,
    )
    
    if shift_id:
        query = query.where(Shift.id == shift_id)
    
    result = await db.execute(query)
    rows = result.all()
    
    items = []
    total_revenue = 0
    total_transactions = 0
    
    for row in rows:
        item = ShiftReportItem(
            shift_id=row.shift_id,
            shift_name=row.shift_name,
            date=row.date,
            operator_id=row.operator_id,
            operator_name=row.operator_name,
            total_transactions=row.total_transactions or 0,
            total_revenue=row.total_revenue or 0,
            cash_revenue=row.cash_revenue or 0,
            emoney_revenue=row.emoney_revenue or 0,
            rfid_revenue=row.rfid_revenue or 0,
            active_transactions=row.active_transactions or 0,
            completed_transactions=row.completed_transactions or 0,
            average_fee=round((row.total_revenue or 0) / max(row.total_transactions or 1, 1), 2),
        )
        items.append(item)
        total_revenue += item.total_revenue
        total_transactions += item.total_transactions
    
    return ShiftReport(
        items=items,
        total_revenue=total_revenue,
        total_transactions=total_transactions,
    )
```

**Step 3: Test**

```bash
curl "http://localhost:8000/api/reports/shift?date_from=2026-04-01&date_to=2026-04-27"
```

Expected: ShiftReport JSON with items grouped by shift and operator.

**Step 4: Commit**

```bash
git add api/app/routes/reports.py api/app/schemas/report.py
git commit -m "feat(reports): add shift-wise report endpoint"
```

---

## Task 11: Add Report Preset Endpoints

**Files:**
- Modify: `api/app/routes/reports.py`

**Step 1: Add convenience endpoints**

```python
from datetime import timedelta


@router.get("/summary/daily", response_model=SummaryReport)
async def get_daily_report(
    report_date: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SummaryReport:
    """Get summary report for a single day."""
    return await get_summary_report(
        date_from=report_date,
        date_to=report_date + timedelta(days=1),
        db=db,
        current_user=current_user,
    )


@router.get("/summary/weekly", response_model=SummaryReport)
async def get_weekly_report(
    year: int = Query(...),
    week: int = Query(..., ge=1, le=53),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SummaryReport:
    """Get summary report for a specific week."""
    from datetime import datetime
    
    # Calculate week start (Monday)
    jan1 = datetime(year, 1, 1).date()
    monday = jan1 + timedelta(days=(week - 1) * 7 - jan1.weekday())
    
    return await get_summary_report(
        date_from=monday,
        date_to=monday + timedelta(days=7),
        db=db,
        current_user=current_user,
    )


@router.get("/summary/monthly", response_model=SummaryReport)
async def get_monthly_report(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SummaryReport:
    """Get summary report for a specific month."""
    from calendar import monthrange
    
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1]) + timedelta(days=1)
    
    return await get_summary_report(
        date_from=start,
        date_to=end,
        db=db,
        current_user=current_user,
    )
```

**Step 2: Test**

```bash
curl "http://localhost:8000/api/reports/summary/daily?date=2026-04-26"
curl "http://localhost:8000/api/reports/summary/monthly?year=2026&month=4"
```

Expected: SummaryReport JSON for the requested period.

**Step 3: Commit**

```bash
git add api/app/routes/reports.py
git commit -m "feat(reports): add daily/weekly/monthly preset endpoints"
```

---

## Task 12: Add Report Export Service

**Files:**
- Create: `api/app/services/report_export.py`
- Modify: `pyproject.toml` (add dependencies)

**Step 1: Add dependencies to pyproject.toml**

```toml
dependencies = [
    # ... existing deps ...
    "openpyxl>=3.1.0",
    "reportlab>=4.0.0",
]
```

**Step 2: Write report_export.py**

```python
"""Report export service — CSV, Excel, PDF."""

import csv
import io
from datetime import date
from typing import Any

from api.app.schemas.report import SummaryReport, EmoneyReport, ShiftReport


def export_summary_csv(report: SummaryReport) -> bytes:
    """Export summary report as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Transactions", report.total_transactions])
    writer.writerow(["Total Revenue", report.total_revenue])
    writer.writerow(["Cash Revenue", report.cash_revenue])
    writer.writerow(["E-Money Revenue", report.emoney_revenue])
    writer.writerow(["RFID Revenue", report.rfid_revenue])
    writer.writerow(["Average Fee", report.average_fee])
    writer.writerow(["Active Transactions", report.active_transactions])
    writer.writerow(["Completed Transactions", report.completed_transactions])
    return output.getvalue().encode("utf-8-sig")


def export_summary_xlsx(report: SummaryReport) -> bytes:
    """Export summary report as Excel."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    
    # Header
    ws["A1"] = "E-Parking Summary Report"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:B1")
    
    # Data
    rows = [
        ["Metric", "Value"],
        ["Total Transactions", report.total_transactions],
        ["Total Revenue", report.total_revenue],
        ["Cash Revenue", report.cash_revenue],
        ["E-Money Revenue", report.emoney_revenue],
        ["RFID Revenue", report.rfid_revenue],
        ["Average Fee", report.average_fee],
        ["Active Transactions", report.active_transactions],
        ["Completed Transactions", report.completed_transactions],
    ]
    
    for i, row in enumerate(rows, start=3):
        for j, value in enumerate(row, start=1):
            cell = ws.cell(row=i, column=j, value=value)
            if i == 3:  # Header row
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
    
    # Auto-width
    for col in range(1, 3):
        ws.column_dimensions[get_column_letter(col)].width = 25
    
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def export_summary_pdf(report: SummaryReport, site_name: str = "E-Parking", date_from: date | None = None, date_to: date | None = None) -> bytes:
    """Export summary report as PDF."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    # Header
    elements.append(Paragraph(f"<b>{site_name}</b>", styles["Title"]))
    if date_from and date_to:
        elements.append(Paragraph(f"Period: {date_from} to {date_to}", styles["Normal"]))
    elements.append(Spacer(1, 20))
    
    # Table
    data = [
        ["Metric", "Value"],
        ["Total Transactions", f"{report.total_transactions:,}"],
        ["Total Revenue", f"Rp {report.total_revenue:,}"],
        ["Cash Revenue", f"Rp {report.cash_revenue:,}"],
        ["E-Money Revenue", f"Rp {report.emoney_revenue:,}"],
        ["RFID Revenue", f"Rp {report.rfid_revenue:,}"],
        ["Average Fee", f"Rp {report.average_fee:,.2f}"],
        ["Active Transactions", f"{report.active_transactions:,}"],
        ["Completed Transactions", f"{report.completed_transactions:,}"],
    ]
    
    table = Table(data, colWidths=[250, 200])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    doc.build(elements)
    return output.getvalue()
```

**Step 3: Install dependencies**

```bash
pip install openpyxl reportlab
```

**Step 4: Commit**

```bash
git add api/app/services/report_export.py pyproject.toml
git commit -m "feat(reports): add CSV, Excel, PDF export service"
```

---

## Task 13: Add Export Endpoints to Reports Router

**Files:**
- Modify: `api/app/routes/reports.py`

**Step 1: Add export endpoints**

```python
from fastapi import Response
from api.app.services.report_export import (
    export_summary_csv,
    export_summary_xlsx,
    export_summary_pdf,
)
from api.app.models.site_config import SiteConfig


@router.get("/summary/export")
async def export_summary(
    format: str = Query(..., regex="^(csv|xlsx|pdf)$"),
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Export summary report in specified format."""
    report = await get_summary_report(date_from, date_to, db, current_user)
    
    # Get site name for PDF header
    site_result = await db.execute(select(SiteConfig))
    site = site_result.scalar_one_or_none()
    site_name = site.name if site else "E-Parking"
    
    if format == "csv":
        content = export_summary_csv(report)
        media_type = "text/csv"
        ext = "csv"
    elif format == "xlsx":
        content = export_summary_xlsx(report)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:  # pdf
        content = export_summary_pdf(report, site_name, date_from, date_to)
        media_type = "application/pdf"
        ext = "pdf"
    
    filename = f"EParking_Report_Summary_{date_from}_{date_to}.{ext}"
    
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**Step 2: Test**

```bash
curl -o report.csv "http://localhost:8000/api/reports/summary/export?format=csv&date_from=2026-04-01&date_to=2026-04-27"
curl -o report.xlsx "http://localhost:8000/api/reports/summary/export?format=xlsx&date_from=2026-04-01&date_to=2026-04-27"
curl -o report.pdf "http://localhost:8000/api/reports/summary/export?format=pdf&date_from=2026-04-01&date_to=2026-04-27"
```

Expected: Files downloaded successfully.

**Step 3: Commit**

```bash
git add api/app/routes/reports.py
git commit -m "feat(reports): add report export endpoints (CSV, Excel, PDF)"
```

---

## Task 14: Update Report UI with Presets and Export

**Files:**
- Modify: `frontend/pages/report.vue`

**Step 1: Add quick preset buttons**

Add above date picker:

```vue
<el-button-group class="mb-2">
  <el-button @click="setToday">Hari Ini</el-button>
  <el-button @click="setThisWeek">Minggu Ini</el-button>
  <el-button @click="setThisMonth">Bulan Ini</el-button>
  <el-button @click="setLastMonth">Bulan Lalu</el-button>
</el-button-group>
```

**Step 2: Add export buttons**

Add to each tab pane after the stats grid:

```vue
<el-divider />
<el-button-group>
  <el-button @click="exportReport('csv')">Export CSV</el-button>
  <el-button @click="exportReport('xlsx')">Export Excel</el-button>
  <el-button @click="exportReport('pdf')">Export PDF</el-button>
</el-button-group>
```

**Step 3: Add methods**

```javascript
function setToday() {
  const today = new Date().toISOString().split('T')[0]
  dateRange.value = [today, today]
  loadReports()
}

function setThisWeek() {
  const now = new Date()
  const monday = new Date(now.setDate(now.getDate() - now.getDay() + 1))
  const sunday = new Date(now.setDate(monday.getDate() + 6))
  dateRange.value = [
    monday.toISOString().split('T')[0],
    sunday.toISOString().split('T')[0],
  ]
  loadReports()
}

function setThisMonth() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  dateRange.value = [
    start.toISOString().split('T')[0],
    end.toISOString().split('T')[0],
  ]
  loadReports()
}

function setLastMonth() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const end = new Date(now.getFullYear(), now.getMonth(), 0)
  dateRange.value = [
    start.toISOString().split('T')[0],
    end.toISOString().split('T')[0],
  ]
  loadReports()
}

async function exportReport(format) {
  if (!dateRange.value || dateRange.value.length !== 2) {
    ElMessage.warning('Please select a date range first')
    return
  }
  const [from, to] = dateRange.value
  const url = `/api/reports/summary/export?format=${format}&date_from=${from}&date_to=${to}`
  
  try {
    const response = await $api.get(url, { responseType: 'blob' })
    const blob = new Blob([response.data])
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `EParking_Report_Summary_${from}_${to}.${format}`
    link.click()
    ElMessage.success(`Report exported as ${format.toUpperCase()}`)
  } catch (e) {
    ElMessage.error('Export failed')
  }
}
```

**Step 4: Test**
- Open Reports page
- Click "Hari Ini" → should auto-fill date and load
- Click "Export CSV" → file should download

**Step 5: Commit**

```bash
git add frontend/pages/report.vue
git commit -m "feat(reports): add preset buttons and export UI"
```

---

## Final Verification

Run the full test suite:

```bash
pytest -x -q --tb=short
```

Expected: All tests pass.

Run linter:

```bash
ruff check .
mypy .
```

Expected: No critical errors.

**Final commit:**

```bash
git commit -m "feat: complete dev tools, deployment installer, site config, and reporting enhancements"
```

---

*Plan created on 26 April 2026. Ready for implementation.*
