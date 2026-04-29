#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# E-Parking v2 — Booth PC Installation Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# Installs a minimal booth PC with:
#   Python 3.12, Google Chrome, booth bridge WebSocket server, serial drivers
#
# Usage:
#   sudo ./setup.sh
#
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/opt/parking-system-v2"
REPO_URL="https://github.com/your-org/parking-system-v2.git"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
step "0/9 — Preflight Checks"

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

if ! grep -q "Ubuntu 22.04" /etc/os-release 2>/dev/null; then
    warn "This script is designed for Ubuntu 22.04 LTS. Continuing anyway..."
    read -rp "Press Enter to continue or Ctrl+C to abort..."
fi

# ── 1. Gather configuration ───────────────────────────────────────────────────
step "1/9 — Configuration"

read -rp "Server IP address (e.g. 192.168.1.100): " SERVER_IP
if [[ -z "$SERVER_IP" ]]; then
    error "Server IP is required"
    exit 1
fi

read -rp "Booth name (e.g. Booth 2): " BOOTH_NAME
BOOTH_NAME=${BOOTH_NAME:-Booth}

read -rp "Booth code (e.g. BOOTH_02): " BOOTH_CODE
BOOTH_CODE=${BOOTH_CODE:-BOOTH}

read -rp "Booth PC IP address (for auto-detection): " BOOTH_IP
if [[ -z "$BOOTH_IP" ]]; then
    BOOTH_IP=$(hostname -I | awk '{print $1}')
    warn "Auto-detected booth IP: ${BOOTH_IP}"
fi

read -rp "Default gate code for this booth (e.g. GOUT02): " GATE_CODE
GATE_CODE=${GATE_CODE:-}

read -rp "E-Money reader serial device [/dev/ttyUSB0]: " EMONEY_DEV
EMONEY_DEV=${EMONEY_DEV:-/dev/ttyUSB0}

read -rp "E-Money reader baudrate [38400]: " EMONEY_BAUD
EMONEY_BAUD=${EMONEY_BAUD:-38400}

read -rp "Receipt printer serial device [/dev/ttyUSB1]: " PRINTER_DEV
PRINTER_DEV=${PRINTER_DEV:-/dev/ttyUSB1}

read -rp "Receipt printer baudrate [9600]: " PRINTER_BAUD
PRINTER_BAUD=${PRINTER_BAUD:-9600}

read -rp "Barcode scanner serial device [/dev/ttyUSB2]: " SCANNER_DEV
SCANNER_DEV=${SCANNER_DEV:-/dev/ttyUSB2}

read -rp "Barcode scanner baudrate [9600]: " SCANNER_BAUD
SCANNER_BAUD=${SCANNER_BAUD:-9600}

read -rp "Enable auto-login for operator? [y/N]: " AUTO_LOGIN
AUTO_LOGIN=${AUTO_LOGIN:-n}

read -rp "Git repository URL [${REPO_URL}]: " INPUT_REPO
REPO_URL=${INPUT_REPO:-$REPO_URL}

# ── 2. Update system ──────────────────────────────────────────────────────────
step "2/9 — Updating System Packages"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq

# ── 3. Install dependencies ───────────────────────────────────────────────────
step "3/9 — Installing Dependencies"

apt-get install -y -qq \
    python3.12 python3.12-venv python3.12-dev python3-pip \
    curl wget git unzip

# Google Chrome
if ! command -v google-chrome &>/dev/null; then
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb
    apt-get install -y -qq /tmp/chrome.deb || apt-get install -fy -qq
    rm -f /tmp/chrome.deb
fi
ok "Google Chrome installed"

# ── 4. Create parking user ────────────────────────────────────────────────────
step "4/9 — Creating System User"

if ! id parking &>/dev/null; then
    useradd -r -s /bin/bash -m -d /home/parking parking
fi
usermod -aG dialout parking
ok "User 'parking' created (groups: $(groups parking))"

# ── 5. Clone repository ───────────────────────────────────────────────────────
step "5/9 — Installing Application"

if [[ -d "$PROJECT_ROOT/.git" ]]; then
    warn "Repository already exists. Pulling latest..."
    cd "$PROJECT_ROOT"
    sudo -u parking git pull origin main
else
    rm -rf "$PROJECT_ROOT"
    git clone "$REPO_URL" "$PROJECT_ROOT"
    chown -R parking:parking "$PROJECT_ROOT"
fi

# Create virtual environment with minimal deps
cd "$PROJECT_ROOT"
if [[ ! -d ".venv" ]]; then
    sudo -u parking python3.12 -m venv .venv
fi

# Only install booth bridge dependencies
sudo -u parking .venv/bin/pip install --quiet --upgrade pip
sudo -u parking .venv/bin/pip install --quiet pyserial websockets
ok "Booth bridge dependencies installed"

# ── 6. Write booth configuration ────────────────────────────────────────────────
step "6/9 — Writing Booth Configuration"

mkdir -p /etc/parking
chown parking:parking /etc/parking

cat > /etc/parking/booth.json <<EOF
{
  "name": "${BOOTH_NAME}",
  "code": "${BOOTH_CODE}",
  "ip_address": "${BOOTH_IP}",
  "default_gate_code": "${GATE_CODE}",
  "peripherals": {
    "emoney_reader": {
      "enabled": true,
      "device": "${EMONEY_DEV}",
      "baudrate": ${EMONEY_BAUD}
    },
    "receipt_printer": {
      "enabled": true,
      "device": "${PRINTER_DEV}",
      "baudrate": ${PRINTER_BAUD}
    },
    "barcode_scanner": {
      "enabled": true,
      "device": "${SCANNER_DEV}",
      "baudrate": ${SCANNER_BAUD}
    },
    "running_text": {
      "enabled": false
    }
  }
}
EOF

chown parking:parking /etc/parking/booth.json
ok "Booth config written to /etc/parking/booth.json"

# ── 7. Install booth bridge service ─────────────────────────────────────────────
step "7/9 — Installing Booth Bridge Service"

# Copy and patch service file for this booth
SERVICE_FILE="/etc/systemd/system/booth-bridge-${BOOTH_CODE,,}.service"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Parking Booth Bridge — ${BOOTH_NAME}
After=network.target

[Service]
Type=simple
User=parking
Group=parking
SupplementaryGroups=dialout
WorkingDirectory=${PROJECT_ROOT}
Environment=PYTHONPATH=${PROJECT_ROOT}
Environment=APP_ENV=production
ExecStart=${PROJECT_ROOT}/.venv/bin/python -m booth_bridge.main --config /etc/parking/booth.json --port 5678
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=booth-bridge-${BOOTH_CODE,,}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$(basename "$SERVICE_FILE")"
systemctl start "$(basename "$SERVICE_FILE")"
ok "Booth bridge service installed and started"

# ── 8. Create Chrome desktop shortcut ───────────────────────────────────────────
step "8/9 — Creating Desktop Shortcut"

DESKTOP_FILE="/home/parking/Desktop/Parking-POS.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Parking POS
Comment=E-Parking POS System
Exec=/usr/bin/google-chrome --app=http://${SERVER_IP} --start-fullscreen --no-first-run --no-default-browser-check --kiosk --disable-infobars
Icon=/usr/share/icons/hicolor/256x256/apps/google-chrome.png
Type=Application
Terminal=false
Categories=Application;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"
chown -R parking:parking "$(dirname "$DESKTOP_FILE")"
ok "Desktop shortcut created for user 'parking'"

# Also create for any existing operator user
for user_dir in /home/*; do
    [[ -d "$user_dir" ]] || continue
    username=$(basename "$user_dir")
    [[ "$username" == "parking" ]] && continue
    
    cp "$DESKTOP_FILE" "$user_dir/Desktop/Parking-POS.desktop"
    chown "$username:$username" "$user_dir/Desktop/Parking-POS.desktop"
    ok "Desktop shortcut copied for user '$username'"
done

# ── 9. Auto-login (optional) ────────────────────────────────────────────────────
step "9/9 — Configuring Auto-Login"

if [[ "$AUTO_LOGIN" =~ ^[Yy]$ ]]; then
    # Detect display manager
    if [[ -f /etc/gdm3/custom.conf ]]; then
        # GDM (GNOME)
        sed -i 's/^#*AutomaticLoginEnable=.*/AutomaticLoginEnable=true/' /etc/gdm3/custom.conf
        sed -i 's/^#*AutomaticLogin=.*/AutomaticLogin=operator/' /etc/gdm3/custom.conf
        ok "GDM auto-login configured for user 'operator'"
    elif [[ -d /etc/lightdm ]]; then
        # LightDM
        mkdir -p /etc/lightdm/lightdm.conf.d
        cat > /etc/lightdm/lightdm.conf.d/50-autologin.conf <<EOF
[Seat:*]
autologin-user=operator
autologin-user-timeout=0
EOF
        ok "LightDM auto-login configured for user 'operator'"
    else
        warn "Unknown display manager. Auto-login not configured."
    fi
else
    info "Auto-login skipped"
fi

# ── Summary ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Booth PC installation complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
info "Booth:      ${BOOTH_NAME} (${BOOTH_CODE})"
info "Server:     http://${SERVER_IP}"
info "Local WS:   ws://localhost:5678"
info "Serial dev: ${EMONEY_DEV}, ${PRINTER_DEV}, ${SCANNER_DEV}"
echo ""
info "Service:"
info "  systemctl status $(basename "$SERVICE_FILE")"
echo ""
warn "Next steps:"
echo "  1. Verify booth bridge: sudo journalctl -u $(basename "$SERVICE_FILE") -f"
echo "  2. Verify serial devices: ls -la /dev/ttyUSB*"
echo "  3. On the SERVER, ensure gate daemons are running:"
echo "       cd /opt/parking-system-v2 && ./scripts/enable-gate-daemons.sh --run"
echo "  4. On the SERVER admin page, ensure POS record exists:"
echo "       Name: ${BOOTH_NAME}"
echo "       Code: ${BOOTH_CODE}"
echo "       IP:   ${BOOTH_IP}"
echo "       Default Gate: ${GATE_CODE}"
echo "  5. Open Chrome shortcut — POS should auto-detect this booth"
echo "  6. Test e-money reader tap and receipt printer"
echo ""
