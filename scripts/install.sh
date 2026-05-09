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
    log_warn "Not Ubuntu 24.04 - proceed with caution"
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
        libpq-dev python3-dev build-essential
    
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
        log_warn "Directory exists - will update"
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
        read -rp "Git repository URL: " repo_url
        if [[ -z "$repo_url" ]]; then
            echo -e "${RED}ERROR: Repository URL required${NC}"
            exit 1
        fi
        git clone "$repo_url" "$APP_DIR"
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

# Phase 8.5: Initialize .env
if [[ ! -f "$APP_DIR/.env" ]]; then
    if [[ -f "$APP_DIR/.env.example" ]]; then
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        log_ok ".env initialized from .env.example — edit credentials before starting services"
    else
        log_warn ".env.example not found — create $APP_DIR/.env manually before starting services"
    fi
fi

# Phase 9: Site Config
if prompt "Configure site information?"; then
    read -rp "Parking site name: " site_name
    read -rp "Address: " site_address
    read -rp "City: " site_city
    read -rp "Phone: " site_phone
    read -rp "Email: " site_email
    
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
    systemctl enable --now parking-api parking-worker-critical parking-worker-bg booth-bridge
    log_ok "Services started"
fi

# Phase 12: Health Check
if prompt "Run health check?"; then
    sleep 3
    if curl -sf http://localhost/api/health >/dev/null 2>&1; then
        log_ok "API is healthy!"
    else
        log_warn "API health check failed - check logs with: journalctl -u parking-api -f"
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
