#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# enable-gate-daemons.sh
#
# Reads all gates from the database and generates (or runs) the systemd
# enable commands for each one.
#
# Usage:
#   ./scripts/enable-gate-daemons.sh          # Print commands only
#   ./scripts/enable-gate-daemons.sh --run    # Actually execute them
#
# This script must run AFTER gates are configured in the Device page.
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN=false

if [[ "${1:-}" == "--run" ]]; then
    RUN=true
fi

# Load .env for DB credentials
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

DB_USER="${DB_USER:-parking}"
DB_NAME="${DB_NAME:-parking}"
DB_PASSWORD="${DB_PASSWORD:-parking_secret}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Check if gates exist
SQL="SELECT code, direction, name FROM gates WHERE is_active = true ORDER BY code;"

echo "Querying database for configured gates..."
echo ""

# Query via psql (fallback to docker if postgres not installed locally)
if command -v psql &>/dev/null; then
    export PGPASSWORD="$DB_PASSWORD"
    RESULT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -F'|' -c "$SQL" 2>/dev/null || true)
else
    # Try docker compose
    RESULT=$(docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -t -A -F'|' -c "$SQL" 2>/dev/null || true)
fi

if [[ -z "$RESULT" ]]; then
    echo "ERROR: No active gates found in database."
    echo ""
    echo "You must configure gates in the web UI first:"
    echo "  1. Open http://<server-ip>"
    echo "  2. Log in as admin"
    echo "  3. Go to Device → Gates"
    echo "  4. Add your gates (e.g. GIN01, GIN02, GOUT01, GOUT02)"
    echo ""
    echo "Then re-run this script."
    exit 1
fi

echo "Found gates:"
echo ""

COMMANDS=()

while IFS='|' read -r code direction name; do
    [[ -z "$code" ]] && continue
    if [[ "$direction" == "IN" ]]; then
        UNIT="parking-daemon-gate-in@${code}"
    else
        UNIT="parking-daemon-gate-out@${code}"
    fi
    echo "  [$direction] $code — $name"
    COMMANDS+=("sudo systemctl enable --now ${UNIT}")
done <<< "$RESULT"

echo ""
echo "Commands to enable gate daemons:"
echo ""

for cmd in "${COMMANDS[@]}"; do
    echo "  $cmd"
done

if $RUN; then
    echo ""
    echo "Executing..."
    echo ""
    for cmd in "${COMMANDS[@]}"; do
        echo "→ $cmd"
        eval "$cmd"
    done
    echo ""
    echo "All gate daemons enabled and started."
    echo "They will auto-start on future reboots."
else
    echo ""
    echo "To execute these commands, run:"
    echo "  ./scripts/enable-gate-daemons.sh --run"
fi

echo ""
echo "Verify status:"
echo "  sudo systemctl status 'parking-daemon-gate-*'"
