#!/usr/bin/env bash
# ============================================================================
# Create Parking POS Desktop Shortcut
# ============================================================================
# Usage: ./create-desktop-shortcut.sh [SERVER_IP] [BOOTH_NAME]
#
# Creates a .desktop launcher on Linux desktop that opens the POS page
# in Chrome app mode (no address bar, looks like native app).
#
# Example:
#   ./create-desktop-shortcut.sh 192.168.1.101 "Booth-01"
# ============================================================================

set -euo pipefail

SERVER_IP="${1:-localhost}"
BOOTH_NAME="${2:-Parking-POS}"
DESKTOP_DIR="${HOME}/Desktop"
ICON_PATH="/opt/parking/assets/logo.png"
APP_URL="http://${SERVER_IP}:3000"

echo "Creating desktop shortcut for ${BOOTH_NAME}..."
echo "  Server: ${APP_URL}"
echo "  Desktop: ${DESKTOP_DIR}"

# Create desktop directory if missing
mkdir -p "${DESKTOP_DIR}"

# Generate .desktop file
cat > "${DESKTOP_DIR}/${BOOTH_NAME}.desktop" <<EOF
[Desktop Entry]
Version=1.0
Name=${BOOTH_NAME}
Comment=Parking System POS
Exec=/usr/bin/google-chrome --app=${APP_URL} --start-fullscreen --no-first-run --no-default-browser-check
Icon=${ICON_PATH}
Type=Application
Terminal=false
Categories=Application;
StartupNotify=true
EOF

# Make executable
chmod +x "${DESKTOP_DIR}/${BOOTH_NAME}.desktop"

# Try to set metadata so it shows as trusted (GNOME)
if command -v gio &> /dev/null; then
    gio set "${DESKTOP_DIR}/${BOOTH_NAME}.desktop" metadata::trusted true 2>/dev/null || true
fi

echo ""
echo "Shortcut created: ${DESKTOP_DIR}/${BOOTH_NAME}.desktop"
echo ""
echo "Double-click the icon to launch the POS in fullscreen app mode."
echo ""
echo "Tip: If Chrome is not installed, change the Exec line to use chromium or firefox:"
echo "  Exec=/usr/bin/chromium --app=${APP_URL} --start-fullscreen"
