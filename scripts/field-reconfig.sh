#!/usr/bin/env bash
# On-site bring-up for a server imaged in the workshop.
#
# The workshop install bakes the workshop's IP into CORS_ORIGINS and mints a
# setup token that may have expired. Run this once on-site after the box has
# its real network address to fix CORS, restart the API, and mint a fresh
# wizard token.
#
# Usage:
#   sudo ./scripts/field-reconfig.sh

set -euo pipefail

PROJECT_ROOT="${PARKING_INSTALL_ROOT:-/opt/parking-system-v2}"
ENV_FILE="${PROJECT_ROOT}/.env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "must run as root (sudo)" >&2
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "no .env at ${ENV_FILE} — run installer/setup.sh --role server first" >&2
    exit 1
fi

DETECTED_IP=$(hostname -I | awk '{print $1}')
read -rp "Server IP on this network [${DETECTED_IP}]: " SERVER_IP
SERVER_IP=${SERVER_IP:-$DETECTED_IP}

# Rewrite CORS_ORIGINS to the on-site address (operator kiosk + booth PCs).
NEW_CORS="http://localhost:3000,http://${SERVER_IP}:3000,http://${SERVER_IP}"
if grep -q '^CORS_ORIGINS=' "$ENV_FILE"; then
    sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=${NEW_CORS}|" "$ENV_FILE"
else
    echo "CORS_ORIGINS=${NEW_CORS}" >> "$ENV_FILE"
fi
echo "CORS_ORIGINS set to ${NEW_CORS}"

# Restart API so the new origins take effect.
systemctl restart parking-api 2>/dev/null || echo "warn: could not restart parking-api"
systemctl reload nginx 2>/dev/null || systemctl restart nginx 2>/dev/null || true
echo "parking-api restarted"

# Mint a fresh wizard token (workshop token likely expired).
bash "${SCRIPT_DIR}/regen-setup-token.sh"
