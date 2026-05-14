#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# E-Parking v2 — Server + Booth Combo Installation Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# This script installs the full server stack AND configures the local machine
# as Booth 1 (the booth physically connected to this server PC).
#
# Use case: Small parking lots where the server PC is also the operator station
#           for one of the exit gates.
#
# Topology (2 IN + 2 OUT):
#   Server PC (this machine)  → Booth 1 (local) + Gate In 1 + Gate In 2 + Gate Out 1
#   Booth PC 2 (separate)     → Booth 2 (remote) + Gate Out 2
#
# Usage:
#   sudo ./setup.sh
#
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# ── 0. Preflight ────────────────────────────────────────────────────────────────
step "0/2 — Preflight Checks"

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

SERVER_IP=$(hostname -I | awk '{print $1}')
info "Detected server IP: ${SERVER_IP}"
info "This script will:"
echo "  1. Install the full server stack (PostgreSQL, Redis, API, nginx)"
echo "  2. Configure this PC as Booth 1 with local serial devices"
echo ""
read -rp "Press Enter to continue or Ctrl+C to abort..."

# ── 1. Run server installer ─────────────────────────────────────────────────────
step "1/2 — Installing Server Stack"

SERVER_SETUP="${SCRIPT_DIR}/../server/setup.sh"
if [[ ! -f "$SERVER_SETUP" ]]; then
    error "Server installer not found at: ${SERVER_SETUP}"
    exit 1
fi

# Pass through to server installer
bash "$SERVER_SETUP"
ok "Server installation complete"

# ── 2. Run local booth installer ────────────────────────────────────────────────
step "2/2 — Configuring Local Booth (Booth 1)"

info "Now configuring this PC as Booth 1..."
echo ""

# Gather booth-specific config
read -rp "Booth 1 name [Booth 1]: " BOOTH_NAME
BOOTH_NAME=${BOOTH_NAME:-Booth 1}

read -rp "Booth 1 code [BOOTH_01]: " BOOTH_CODE
BOOTH_CODE=${BOOTH_CODE:-BOOTH_01}

read -rp "Default gate for Booth 1 (e.g. GOUT01): " GATE_CODE
if [[ -z "$GATE_CODE" ]]; then
    error "Default gate code is required"
    exit 1
fi

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

read -rp "Barrier gate connection type (tcp/serial) [tcp]: " GATE_TYPE
GATE_TYPE=${GATE_TYPE:-tcp}

GATE_DEV=""
GATE_BAUD=9600
if [[ "$GATE_TYPE" == "serial" ]]; then
    read -rp "Barrier gate serial device [/dev/ttyUSB3]: " GATE_DEV_INPUT
    GATE_DEV=${GATE_DEV_INPUT:-/dev/ttyUSB3}
    read -rp "Barrier gate baudrate [9600]: " GATE_BAUD_INPUT
    GATE_BAUD=${GATE_BAUD_INPUT:-9600}
fi

read -rp "Enable auto-login for operator? [y/N]: " AUTO_LOGIN
AUTO_LOGIN=${AUTO_LOGIN:-n}

PROJECT_ROOT="/opt/parking-system-v2"

# Write booth config
mkdir -p /etc/parking
chown parking:parking /etc/parking

cat > /etc/parking/booth.json <<EOF
{
  "name": "${BOOTH_NAME}",
  "code": "${BOOTH_CODE}",
  "ip_address": "${SERVER_IP}",
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
ok "Booth config written"

# Write install notes for technician reference
NOTES_FILE="/etc/parking/install-notes.txt"
cat > "$NOTES_FILE" <<EOF
E-Parking v2 — Installation Notes
Generated: $(date)
════════════════════════════════════════

BOOTH: ${BOOTH_NAME} (${BOOTH_CODE})
  Default gate : ${GATE_CODE}
  POS IP       : ${SERVER_IP}

PERIPHERALS:
  E-Money reader : ${EMONEY_DEV}  (${EMONEY_BAUD} baud)
  Receipt printer: ${PRINTER_DEV}  (${PRINTER_BAUD} baud)
  Barcode scanner: ${SCANNER_DEV}  (${SCANNER_BAUD} baud)

BARRIER GATE (${GATE_CODE}):
  Connection type: ${GATE_TYPE}
EOF

if [[ "$GATE_TYPE" == "serial" ]]; then
    cat >> "$NOTES_FILE" <<EOF
  Serial device  : ${GATE_DEV}  (${GATE_BAUD} baud)

  ↳ In admin UI → Device → Gates → ${GATE_CODE}, set:
      protocol         = serial
      controller_device= ${GATE_DEV}
      controller_baudrate= ${GATE_BAUD}
EOF
    if [[ -n "$(ls /dev/parking-rfid 2>/dev/null || true)" ]]; then
        cat >> "$NOTES_FILE" <<EOF

  RFID (serial gate — Wiegand not available):
    Since this gate has no Wiegand port, RFID requires a direct serial reader.
    In admin UI → Device → Gates → ${GATE_CODE} → hardware_config:
      rfid.enabled          = true
      rfid.connection       = direct_serial
      rfid.device           = /dev/parking-rfid
EOF
    fi
else
    cat >> "$NOTES_FILE" <<EOF
  TCP controller IP and port configured during server install.
EOF
fi

cat >> "$NOTES_FILE" <<EOF

════════════════════════════════════════
View anytime: cat ${NOTES_FILE}
EOF

chown parking:parking "$NOTES_FILE"
ok "Install notes written to ${NOTES_FILE}"

# Install booth bridge service
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

# Create Chrome desktop shortcut (points to localhost)
DESKTOP_FILE="/home/parking/Desktop/Parking-POS.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Parking POS
Comment=E-Parking POS System
Exec=/usr/bin/google-chrome --app=http://localhost --start-fullscreen --no-first-run --no-default-browser-check --kiosk --disable-infobars
Icon=/usr/share/icons/hicolor/256x256/apps/google-chrome.png
Type=Application
Terminal=false
Categories=Application;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"
chown -R parking:parking "$(dirname "$DESKTOP_FILE")"
ok "Desktop shortcut created"

# Auto-login (optional)
if [[ "$AUTO_LOGIN" =~ ^[Yy]$ ]]; then
    if [[ -f /etc/gdm3/custom.conf ]]; then
        sed -i 's/^#*AutomaticLoginEnable=.*/AutomaticLoginEnable=true/' /etc/gdm3/custom.conf
        sed -i 's/^#*AutomaticLogin=.*/AutomaticLogin=operator/' /etc/gdm3/custom.conf
        ok "GDM auto-login configured"
    elif [[ -d /etc/lightdm ]]; then
        mkdir -p /etc/lightdm/lightdm.conf.d
        cat > /etc/lightdm/lightdm.conf.d/50-autologin.conf <<EOF
[Seat:*]
autologin-user=operator
autologin-user-timeout=0
EOF
        ok "LightDM auto-login configured"
    fi
fi

# ── Summary ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Server + Booth 1 installation complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
info "Server:     http://${SERVER_IP}"
info "Local POS:  http://localhost (kiosk mode)"
info "API:        http://${SERVER_IP}/api"
info "Booth:      ${BOOTH_NAME} (${BOOTH_CODE}) → ${GATE_CODE}"
echo ""
info "All services:"
info "  systemctl status parking-api"
info "  systemctl status parking-worker-critical"
info "  systemctl status parking-worker-bg"
info "  systemctl status $(basename "$SERVICE_FILE")"
info "  systemctl status nginx"
echo ""
info "Install notes: cat /etc/parking/install-notes.txt"
echo ""
warn "Next steps:"
echo "  1. Log in as admin at http://${SERVER_IP}"
echo "  2. Add gate records: GIN01, GIN02, GOUT01, GOUT02"
if [[ "$GATE_TYPE" == "serial" ]]; then
    echo "     ↳ For the RS232/USB gate (${GATE_CODE}): set protocol=serial, controller_device=${GATE_DEV}"
else
    echo "     ↳ Use protocol=tcp (compass) with controller IP for each gate"
fi
echo "  3. Add POS record: ${BOOTH_NAME} / ${BOOTH_CODE} / IP=${SERVER_IP} / Gate=${GATE_CODE}"
echo "  4. Link ${GATE_CODE} to POS ${BOOTH_CODE}"
echo "  5. Set up Booth PC 2 (run installer/booth_pc/setup.sh on the 2nd PC)"
echo "  6. Start gate daemons (reads config from DB, auto-starts on boot):"
if [[ "$GATE_TYPE" == "serial" ]]; then
    echo "       sudo /opt/parking-system-v2/scripts/enable-gate-daemons.sh --run --include-local-serial"
    echo "     ↳ --include-local-serial enables RS232/USB gate daemon on this machine too"
else
    echo "       sudo /opt/parking-system-v2/scripts/enable-gate-daemons.sh --run"
fi
echo "  7. Open Parking POS shortcut on this PC to test Booth 1"
echo ""
