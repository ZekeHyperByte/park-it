#!/usr/bin/env bash
#
# E-Parking v2 — Installer
#
# Bootstraps a fresh booth/server PC: OS deps, repo, venv, DB, services,
# udev rules, systemd units. Idempotent — safe to re-run.
#
# Usage:
#   sudo ./install.sh [--gate-id GIN-01 GOUT-01]
#
# Env overrides:
#   INSTALL_DIR   default /opt/eparking
#   APP_USER      default eparking (created if missing)
#   PG_PASSWORD   default 'parking' (only on first install)
#

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/eparking}"
APP_USER="${APP_USER:-eparking}"
PG_PASSWORD="${PG_PASSWORD:-parking}"
APP_TIMEZONE="${APP_TIMEZONE:-Asia/Jakarta}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

GATE_IDS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --gate-id) shift; while [ $# -gt 0 ] && [[ "$1" != --* ]]; do GATE_IDS+=("$1"); shift; done ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

log()  { printf '\033[1;34m[install]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[install]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[install]\033[0m %s\n' "$*" >&2; exit 1; }

[ "$EUID" -eq 0 ] || die "Run as root (sudo)."

# ---------------------------------------------------------------------------
# 1. Detect distro + install OS packages
# ---------------------------------------------------------------------------
detect_distro() {
  if   command -v pacman >/dev/null; then echo arch
  elif command -v apt-get >/dev/null; then echo debian
  else die "Unsupported distro (need pacman or apt-get)."
  fi
}

DISTRO=$(detect_distro)
log "Detected distro: $DISTRO"

install_packages_arch() {
  pacman -Sy --noconfirm --needed \
    python python-pip python-virtualenv \
    docker docker-compose nodejs npm \
    pcsclite ccid \
    postgresql-libs \
    git curl jq
  systemctl enable --now docker
  systemctl enable --now pcscd
}

install_packages_debian() {
  apt-get update
  apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    docker.io docker-compose \
    nodejs npm \
    pcscd libpcsclite-dev libccid \
    libpq5 \
    git curl jq
  systemctl enable --now docker
  systemctl enable --now pcscd
}

log "Installing OS packages..."
case "$DISTRO" in
  arch)   install_packages_arch ;;
  debian) install_packages_debian ;;
esac

# ---------------------------------------------------------------------------
# 1b. System timezone
# ---------------------------------------------------------------------------
# Settlement files + transaction timestamps are operational-local time (WIB).
# A mismatched system clock corrupts the daily Multibank cut, so pin the zone.
current_tz="$(timedatectl show -p Timezone --value 2>/dev/null || echo "")"
if [ "$current_tz" != "$APP_TIMEZONE" ]; then
  log "Setting system timezone to $APP_TIMEZONE (was: ${current_tz:-unknown})..."
  timedatectl set-timezone "$APP_TIMEZONE" || warn "Failed to set timezone — set $APP_TIMEZONE manually before go-live."
else
  log "Timezone already $APP_TIMEZONE."
fi

# ---------------------------------------------------------------------------
# 2. App user
# ---------------------------------------------------------------------------
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  log "Creating system user $APP_USER..."
  useradd -r -m -d "$INSTALL_DIR" -s /usr/bin/bash "$APP_USER"
fi
usermod -aG docker,input,uucp,dialout "$APP_USER" 2>/dev/null || true

# ---------------------------------------------------------------------------
# 3. Repo into INSTALL_DIR
# ---------------------------------------------------------------------------
if [ "$REPO_DIR" != "$INSTALL_DIR" ]; then
  log "Syncing repo to $INSTALL_DIR..."
  mkdir -p "$INSTALL_DIR"
  rsync -a --delete --exclude='.git' --exclude='.venv' --exclude='node_modules' \
    --exclude='frontend/.nuxt' --exclude='frontend/.output' \
    "$REPO_DIR/" "$INSTALL_DIR/"
fi
chown -R "$APP_USER:$APP_USER" "$INSTALL_DIR"

# ---------------------------------------------------------------------------
# 4. Python venv + deps
# ---------------------------------------------------------------------------
log "Setting up Python venv..."
sudo -u "$APP_USER" bash -lc "
  cd '$INSTALL_DIR'
  python -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -e '.[dev]'
  .venv/bin/pip install evdev pyscard
"

# ---------------------------------------------------------------------------
# 5. .env (first install only)
# ---------------------------------------------------------------------------
if [ ! -f "$INSTALL_DIR/.env" ]; then
  log "Creating .env from .env.example..."
  sudo -u "$APP_USER" cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
  sudo -u "$APP_USER" sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$PG_PASSWORD|" "$INSTALL_DIR/.env"
  warn "Edit $INSTALL_DIR/.env to set JWT_SECRET, INTERNAL_API_KEY, etc."
fi

# ---------------------------------------------------------------------------
# 6. Postgres + Redis via docker-compose
# ---------------------------------------------------------------------------
log "Starting postgres + redis..."
sudo -u "$APP_USER" bash -lc "cd '$INSTALL_DIR' && docker compose up -d"

# Wait for postgres
for i in $(seq 1 30); do
  if sudo -u "$APP_USER" docker exec parking-postgres pg_isready -U parking >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# ---------------------------------------------------------------------------
# 7. Alembic migrations + seed (first install only)
# ---------------------------------------------------------------------------
log "Running migrations..."
sudo -u "$APP_USER" bash -lc "cd '$INSTALL_DIR' && .venv/bin/alembic upgrade head"

if [ ! -f "$INSTALL_DIR/.seeded" ]; then
  log "Seeding initial data..."
  sudo -u "$APP_USER" bash -lc "cd '$INSTALL_DIR' && .venv/bin/python scripts/seed.py" || warn "Seed failed (already seeded?)"
  sudo -u "$APP_USER" touch "$INSTALL_DIR/.seeded"
fi

# ---------------------------------------------------------------------------
# 8. Frontend build
# ---------------------------------------------------------------------------
log "Building frontend..."
sudo -u "$APP_USER" bash -lc "
  cd '$INSTALL_DIR/frontend'
  npm install --no-audit --no-fund
  npm run build
"

# ---------------------------------------------------------------------------
# 9. udev rules — Omnikey + serial relay
# ---------------------------------------------------------------------------
log "Installing udev rules..."
cat > /etc/udev/rules.d/99-eparking.rules <<EOF
# Omnikey 5427 CK — HID keyboard mode (0x5427)
KERNEL=="event*", SUBSYSTEM=="input", ATTRS{idVendor}=="076b", ATTRS{idProduct}=="5427", MODE="0660", OWNER="$APP_USER", GROUP="input"
# Omnikey 5427 CK — CCID admin mode (0x5428) — for diagnostics only
KERNEL=="event*", SUBSYSTEM=="input", ATTRS{idVendor}=="076b", ATTRS{idProduct}=="5428", MODE="0660", OWNER="$APP_USER", GROUP="input"
# USB-serial relay / barrier controller (CH340, FTDI, PL2303)
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0660", OWNER="$APP_USER", GROUP="uucp"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0660", OWNER="$APP_USER", GROUP="uucp"
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", MODE="0660", OWNER="$APP_USER", GROUP="uucp"
EOF
udevadm control --reload-rules
udevadm trigger --subsystem-match=input --subsystem-match=tty

# ---------------------------------------------------------------------------
# 10. Systemd units
# ---------------------------------------------------------------------------
log "Installing systemd units..."
for unit in "$INSTALL_DIR/systemd"/*.service "$INSTALL_DIR/systemd"/*.timer; do
  [ -e "$unit" ] || continue
  cp "$unit" /etc/systemd/system/
done
systemctl daemon-reload

# Enable + start core services
systemctl enable --now parking-api.service
systemctl enable --now parking-worker-critical.service
systemctl enable --now parking-worker-snapshot.service
systemctl enable --now parking-worker-bg.service
systemctl enable --now booth-bridge.service 2>/dev/null || warn "booth-bridge.service skipped (no booth config yet)"

# Per-gate daemons
for gid in "${GATE_IDS[@]}"; do
  log "Enabling gate daemon for $gid..."
  case "$gid" in
    GIN-*) systemctl enable --now "parking-daemon-gate-in@$gid.service" ;;
    GOUT-*) systemctl enable --now "parking-daemon-gate-out@$gid.service" ;;
    *) warn "Unknown gate prefix in $gid (expected GIN-* or GOUT-*)" ;;
  esac
done

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
cat <<EOF

\033[1;32m[install] Done.\033[0m

Next steps:
  1. Edit $INSTALL_DIR/.env (JWT_SECRET, INTERNAL_API_KEY, CORS_ORIGINS)
  2. Open http://localhost:8000/api/docs to verify API
  3. Open http://localhost:3000/setup to configure gates, POS booths, members
  4. For each Omnikey reader: flip to HID keyboard mode via HID Workbench (Windows)
  5. For each gate, set hardware_config.open_command in /setup or DB
  6. Re-run with --gate-id to enable daemons:
     sudo $0 --gate-id GIN-01 GOUT-01

Logs:
  journalctl -u parking-api -f
  journalctl -u booth-bridge -f
  journalctl -u 'parking-daemon-gate-in@*' -f

EOF
