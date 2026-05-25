#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# enable-gate-daemons.sh
#
# Reads all gates from the database and generates (or runs) the systemd
# enable commands for each one.
#
# Usage:
#   ./scripts/enable-gate-daemons.sh                              # Print only
#   ./scripts/enable-gate-daemons.sh --run                        # TCP gates
#   ./scripts/enable-gate-daemons.sh --run --include-local-serial # TCP + serial
#
# --include-local-serial: also enable RS232/USB gates on THIS machine.
# Use on server+booth combo PC where the serial gate is physically attached.
# Omit on a dedicated server — serial gates belong on the booth PC.
#
# This script must run AFTER gates are configured in the Device page.
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN=false
INCLUDE_LOCAL_SERIAL=false
JSON=false

for arg in "$@"; do
    case "$arg" in
        --run)                  RUN=true ;;
        --include-local-serial) INCLUDE_LOCAL_SERIAL=true ;;
        --json)                 JSON=true ;;
    esac
done

emit() { $JSON || echo "$@"; }

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
SQL="SELECT code, direction, name, protocol, controller_host, controller_device FROM gates WHERE is_active = true ORDER BY code;"

emit "Querying database for configured gates..."
emit ""

# Query via psql (fallback to docker if postgres not installed locally)
if command -v psql &>/dev/null; then
    export PGPASSWORD="$DB_PASSWORD"
    RESULT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -F'|' -c "$SQL" 2>/dev/null || true)
else
    # Try docker compose
    RESULT=$(docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -t -A -F'|' -c "$SQL" 2>/dev/null || true)
fi

if [[ -z "$RESULT" ]]; then
    if $JSON; then
        printf '{"ok":false,"error":"no active gates"}\n'
        exit 1
    fi
    echo "ERROR: No active gates found in database."
    echo ""
    echo "You must configure gates in the web UI first:"
    echo "  1. Open http://<server-ip>"
    echo "  2. Log in as admin"
    echo "  3. Go to Device → Gates"
    echo "  4. Add your gates (e.g. GIN-01, GIN-02, GOUT-01, GOUT-02)"
    echo ""
    echo "Then re-run this script."
    exit 1
fi

echo "Found gates:"
echo ""

COMMANDS=()
SERIAL_GATES=()

SKIPPED_OUT=0
while IFS='|' read -r code direction name protocol controller_host controller_device; do
    [[ -z "$code" ]] && continue
    # Exit lanes have no autonomous daemon (gate_out removed in f4a3eb0).
    # booth_bridge drives the exit relay directly, so skip OUT gates here.
    if [[ "$direction" != "IN" ]]; then
        emit "  [$direction] $code — $name  [exit lane: driven by booth_bridge, no daemon]"
        SKIPPED_OUT=$((SKIPPED_OUT + 1))
        continue
    fi
    UNIT="parking-daemon-gate-in@${code}"

    if [[ "$protocol" == "serial" ]]; then
        if $INCLUDE_LOCAL_SERIAL && [[ -n "$controller_device" ]] && [[ -e "$controller_device" ]]; then
            echo "  [$direction] $code — $name  [RS232/USB ${controller_device} — enabling locally]"
            COMMANDS+=("sudo systemctl enable --now ${UNIT}")
        elif $INCLUDE_LOCAL_SERIAL && [[ -n "$controller_device" ]] && [[ ! -e "$controller_device" ]]; then
            echo "  [$direction] $code — $name  [RS232/USB ${controller_device} — device not found on this machine, skipping]"
            SERIAL_GATES+=("$code|$direction|$name|$UNIT|$controller_device")
        else
            echo "  [$direction] $code — $name  [RS232/USB — run on booth PC with ${controller_device}]"
            SERIAL_GATES+=("$code|$direction|$name|$UNIT|$controller_device")
        fi
    else
        echo "  [$direction] $code — $name  [TCP: ${controller_host}]"
        COMMANDS+=("sudo systemctl enable --now ${UNIT}")
    fi
done <<< "$RESULT"

echo ""
if $INCLUDE_LOCAL_SERIAL; then
    echo "Gate daemon commands (TCP + local RS232/USB):"
else
    echo "TCP gate daemon commands (run on server):"
fi
echo ""

for cmd in "${COMMANDS[@]}"; do
    echo "  $cmd"
done

if [[ ${#SERIAL_GATES[@]} -gt 0 ]]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  RS232/USB gates — must run on the booth PC with USB access"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    for entry in "${SERIAL_GATES[@]}"; do
        IFS='|' read -r scode sdirection sname sunit sdevice <<< "$entry"
        echo "  [$sdirection] $scode — $sname  (device: ${sdevice})"
        echo "    → On booth PC where ${sdevice} is plugged in:"
        echo "         sudo systemctl enable --now ${sunit}"
        echo "    → Verify that booth PC .env has REDIS_HOST pointing to this server"
    done
    echo ""
fi

if $RUN; then
    if [[ ${#COMMANDS[@]} -gt 0 ]]; then
        emit ""
        emit "Executing..."
        emit ""
        FAILED=0
        for cmd in "${COMMANDS[@]}"; do
            emit "→ $cmd"
            if ! eval "$cmd" >/dev/null 2>&1; then
                FAILED=$((FAILED + 1))
                emit "  ✗ failed"
            fi
        done
        if $JSON; then
            printf '{"ok":%s,"enabled":%d,"failed":%d,"serial_pending":%d}\n' \
                $([ $FAILED -eq 0 ] && echo true || echo false) \
                ${#COMMANDS[@]} "$FAILED" "${#SERIAL_GATES[@]}"
            exit $([ $FAILED -eq 0 ] && echo 0 || echo 1)
        fi
        echo ""
        echo "Gate daemons enabled and started."
    fi
    if [[ ${#SERIAL_GATES[@]} -gt 0 ]]; then
        echo ""
        echo "SKIPPED RS232/USB gates — run the commands above on each booth PC."
        echo "Or re-run with --include-local-serial if the gate is on this machine."
    fi
    echo "Daemons will auto-start on future reboots."
else
    echo ""
    if [[ ${#SERIAL_GATES[@]} -gt 0 ]]; then
        echo "Server+booth combo (serial gate on this machine):"
        echo "  ./scripts/enable-gate-daemons.sh --run --include-local-serial"
        echo ""
        echo "Dedicated server (serial gates on separate booth PCs):"
    fi
    echo "  ./scripts/enable-gate-daemons.sh --run"
fi

echo ""
echo "Verify status:"
echo "  sudo systemctl status 'parking-daemon-gate-*'"
