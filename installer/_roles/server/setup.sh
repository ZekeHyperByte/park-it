#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# E-Parking v2 — Server Installation Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# This script installs the full E-Parking v2 server stack:
#   PostgreSQL 16, Redis, nginx, Python 3.12, Node.js, Google Chrome
#   Clones the repo, builds the frontend, installs systemd services.
#
# Usage:
#   sudo ./setup.sh
#
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/opt/parking-system-v2"
REPO_URL="https://github.com/your-org/parking-system-v2.git"  # <-- update this

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

step() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
}

# ── 0. Preflight checks ───────────────────────────────────────────────────────
step "0/12 — Preflight Checks"

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

if ! grep -q "Ubuntu 22.04" /etc/os-release 2>/dev/null; then
    warn "This script is designed for Ubuntu 22.04 LTS. Continuing anyway..."
    read -rp "Press Enter to continue or Ctrl+C to abort..."
fi

# ── 1. Gather configuration ───────────────────────────────────────────────────
step "1/12 — Configuration"

SERVER_IP=$(hostname -I | awk '{print $1}')
read -rp "Server IP address [${SERVER_IP}]: " INPUT_IP
SERVER_IP=${INPUT_IP:-$SERVER_IP}

read -rsp "PostgreSQL password for 'parking' user [parking_secret]: " DB_PASS
echo
DB_PASS=${DB_PASS:-parking_secret}

read -rsp "JWT secret (64+ random chars recommended): " JWT_SECRET
echo
if [[ -z "$JWT_SECRET" ]]; then
    JWT_SECRET=$(openssl rand -hex 32)
    warn "Generated random JWT secret"
fi

read -rp "Git repository URL [${REPO_URL}]: " INPUT_REPO
REPO_URL=${INPUT_REPO:-$REPO_URL}

# ── 2. Update system ──────────────────────────────────────────────────────────
step "2/12 — Updating System Packages"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq

# ── 3. Install dependencies ───────────────────────────────────────────────────
step "3/12 — Installing Dependencies"

apt-get install -y -qq \
    postgresql-16 postgresql-client-16 postgresql-contrib-16 \
    redis-server \
    nginx \
    python3.12 python3.12-venv python3.12-dev python3-pip \
    curl wget git unzip \
    ffmpeg

# Node.js 20
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
fi
ok "Node.js $(node -v) installed"

# Google Chrome
if ! command -v google-chrome &>/dev/null; then
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb
    apt-get install -y -qq /tmp/chrome.deb || apt-get install -fy -qq
    rm -f /tmp/chrome.deb
fi
ok "Google Chrome installed"

# ── 4. Create parking user ────────────────────────────────────────────────────
step "4/12 — Creating System User"

if ! id parking &>/dev/null; then
    useradd -r -s /bin/bash -m -d /home/parking parking
fi
usermod -aG dialout parking
ok "User 'parking' created (groups: $(groups parking))"

# ── 5. Configure PostgreSQL ───────────────────────────────────────────────────
step "5/12 — Configuring PostgreSQL"

sudo -u postgres psql -c "CREATE USER parking WITH PASSWORD '${DB_PASS}';" 2>/dev/null || ok "User 'parking' already exists"
sudo -u postgres psql -c "CREATE DATABASE parking OWNER parking;" 2>/dev/null || ok "Database 'parking' already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE parking TO parking;"

# Allow local connections with md5
PG_HBA="/etc/postgresql/16/main/pg_hba.conf"
if ! grep -q "parking" "$PG_HBA"; then
    echo "local   parking   parking   md5" >> "$PG_HBA"
    systemctl restart postgresql
fi
ok "PostgreSQL configured"

# ── 6. Configure Redis ────────────────────────────────────────────────────────
step "6/12 — Configuring Redis"

systemctl enable redis-server
systemctl start redis-server
ok "Redis enabled and started"

# ── 7. Clone and install application ──────────────────────────────────────────
step "7/12 — Installing Application"

if [[ -d "$PROJECT_ROOT/.git" ]]; then
    warn "Repository already exists at ${PROJECT_ROOT}. Pulling latest..."
    cd "$PROJECT_ROOT"
    sudo -u parking git pull origin main
else
    rm -rf "$PROJECT_ROOT"
    git clone "$REPO_URL" "$PROJECT_ROOT"
    chown -R parking:parking "$PROJECT_ROOT"
fi

cd "$PROJECT_ROOT"

# Create virtual environment
if [[ ! -d ".venv" ]]; then
    sudo -u parking python3.12 -m venv .venv
fi

# Install Python dependencies
sudo -u parking .venv/bin/pip install --quiet --upgrade pip
sudo -u parking .venv/bin/pip install --quiet -e ".[dev]"
ok "Python dependencies installed"

# ── 8. Environment file ───────────────────────────────────────────────────────
step "8/12 — Writing Environment Configuration"

cat > "$PROJECT_ROOT/.env" <<EOF
# Auto-generated by installer/server/setup.sh on $(date -Iseconds)
APP_ENV=production
DEBUG=false

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=parking
DB_USER=parking
DB_PASSWORD=${DB_PASS}
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Security
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS (server + booth PCs on local network)
CORS_ORIGINS=http://localhost:3000,http://${SERVER_IP}:3000
EOF

chown parking:parking "$PROJECT_ROOT/.env"
chmod 600 "$PROJECT_ROOT/.env"
ok ".env written to ${PROJECT_ROOT}"

# ── 9. Database migrations ──────────────────────────────────────────────────────
step "9/12 — Running Database Migrations"

cd "$PROJECT_ROOT"
sudo -u parking .venv/bin/alembic upgrade head
ok "Alembic migrations applied"

# ── 10. Build frontend ──────────────────────────────────────────────────────────
step "10/12 — Building Frontend"

cd "$PROJECT_ROOT/frontend"
if [[ ! -d "node_modules" ]]; then
    sudo -u parking npm ci
fi

# Build with empty apiBaseUrl so relative /api/ works through nginx
sudo -u parking bash -c 'NUXT_PUBLIC_API_BASE_URL="" npm run build'
ok "Frontend built"

# ── 11. Install systemd services ────────────────────────────────────────────────
step "11/12 — Installing Systemd Services"

services=(
    "parking-api.service"
    "parking-worker-critical.service"
    "parking-worker-bg.service"
)

for svc in "${services[@]}"; do
    cp "$PROJECT_ROOT/systemd/$svc" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable "$svc"
    systemctl start "$svc"
    ok "${svc} installed and started"
done

# Create app data directories
mkdir -p /var/lib/parking/{snapshots,settlements,logs}
chown -R parking:parking /var/lib/parking

# ── 11b. Drop sudoers rule for setup wizard ────────────────────────────────────
step "11b/12 — Sudoers Drop for Wizard"

cat > /etc/sudoers.d/parking-setup <<EOF
# Allow the parking user to invoke setup wizard helpers without a password.
# Audited by /etc/audit/rules.d if enabled.
parking ALL=(root) NOPASSWD: ${PROJECT_ROOT}/scripts/detect-serial-devices.sh
parking ALL=(root) NOPASSWD: ${PROJECT_ROOT}/scripts/enable-gate-daemons.sh
parking ALL=(root) NOPASSWD: /usr/bin/systemctl start parking-daemon-gate-*
parking ALL=(root) NOPASSWD: /usr/bin/systemctl enable parking-daemon-gate-*
parking ALL=(root) NOPASSWD: /usr/bin/systemctl restart parking-daemon-gate-*
parking ALL=(root) NOPASSWD: /usr/bin/udevadm control --reload-rules
parking ALL=(root) NOPASSWD: /usr/bin/udevadm trigger *
parking ALL=(root) NOPASSWD: /usr/bin/udevadm settle *
EOF
chmod 0440 /etc/sudoers.d/parking-setup
if ! visudo -cf /etc/sudoers.d/parking-setup >/dev/null; then
    error "sudoers drop failed validation; aborting."
    rm -f /etc/sudoers.d/parking-setup
    exit 1
fi
ok "Sudoers drop installed at /etc/sudoers.d/parking-setup"

# ── 11c. Generate one-time setup token ─────────────────────────────────────────
step "11c/12 — Setup Wizard Token"

mkdir -p /etc/parking
SETUP_TOKEN=$(openssl rand -hex 32)
echo -n "$SETUP_TOKEN" > /etc/parking/setup-token
chown root:parking /etc/parking/setup-token
chmod 0640 /etc/parking/setup-token
ok "Token written to /etc/parking/setup-token"

# ── 12. Configure nginx ─────────────────────────────────────────────────────────
step "12/12 — Configuring Nginx"

cat > /etc/nginx/sites-available/parking <<'EOF'
server {
    listen 80;
    server_name _;

    # Frontend (Nuxt SSR / static)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Metrics (internal only)
    location /metrics {
        proxy_pass http://localhost:8000;
        allow 127.0.0.1;
        allow 192.168.0.0/16;
        allow 10.0.0.0/8;
        deny all;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/parking /etc/nginx/sites-enabled/parking
nginx -t && systemctl restart nginx
ok "Nginx configured and restarted"

# ── Summary ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Server installation complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
info "API:        http://${SERVER_IP}:8000"
info "Frontend:   http://${SERVER_IP}:3000"
info "API Docs:   http://${SERVER_IP}:8000/docs"
echo ""
info "Services:"
info "  systemctl status parking-api"
info "  systemctl status parking-worker-critical"
info "  systemctl status parking-worker-bg"
info "  systemctl status nginx"
echo ""
SETUP_URL="http://${SERVER_IP}/setup?token=${SETUP_TOKEN}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  OPEN THIS LINK ON THE INSTALLER LAPTOP TO FINISH CONFIGURATION${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "  ${SETUP_URL}"
echo ""
echo "  Token expires when redeemed or after 24h, whichever comes first."
echo "  Regenerate by re-running this script if you lose it."

# Auto-launch Chrome if a desktop session is present.
if [[ -n "${DISPLAY:-}" ]] && command -v google-chrome &>/dev/null; then
    sudo -u "${SUDO_USER:-parking}" google-chrome "$SETUP_URL" >/dev/null 2>&1 &
    ok "Launched Chrome at ${SETUP_URL}"
fi
echo ""
