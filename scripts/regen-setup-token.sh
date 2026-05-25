#!/usr/bin/env bash
# Regenerate the one-time setup-wizard token.
#
# The token written at install time expires after 24h (mtime-based, see
# api/app/services/setup.py). A server imaged in the workshop and deployed
# on-site days later has a dead token. Run this on the box to mint a fresh
# one and print the wizard URL.
#
# Usage:
#   sudo ./scripts/regen-setup-token.sh

set -euo pipefail

TOKEN_PATH="${SETUP_TOKEN_PATH:-/etc/parking/setup-token}"

if [[ $EUID -ne 0 ]]; then
    echo "must run as root (sudo)" >&2
    exit 1
fi

mkdir -p "$(dirname "$TOKEN_PATH")"
TOKEN=$(openssl rand -hex 32)
echo -n "$TOKEN" > "$TOKEN_PATH"
chown root:parking "$TOKEN_PATH" 2>/dev/null || true
chmod 0640 "$TOKEN_PATH"

SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Setup token regenerated at ${TOKEN_PATH}"
echo
echo "Open on the installer laptop (valid 24h):"
echo "  http://${SERVER_IP}/setup?token=${TOKEN}"
