#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDS_DIR="$PROJECT_ROOT/pids"
STOP_INFRA=false

if [[ "${1:-}" == "--infra" ]]; then
    STOP_INFRA=true
fi

echo "=== E-Parking v2 Development Stop ==="

# Stop services by PID
for service in api frontend; do
    pid_file="$PIDS_DIR/$service.pid"
    if [[ -f "$pid_file" ]]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Stopping $service (PID $pid)..."
            kill "$pid" || true
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                echo "  Force killing $service..."
                kill -9 "$pid" || true
            fi
        fi
        rm -f "$pid_file"
    fi
done

# Stop daemons if any
for pid_file in "$PIDS_DIR"/daemon-*.pid; do
    [[ -f "$pid_file" ]] || continue
    pid=$(cat "$pid_file")
    service=$(basename "$pid_file" .pid)
    if kill -0 "$pid" 2>/dev/null; then
        echo "  Stopping $service (PID $pid)..."
        kill "$pid" || true
    fi
    rm -f "$pid_file"
done

if $STOP_INFRA; then
    echo "  Stopping Docker infrastructure..."
    cd "$PROJECT_ROOT"
    docker compose down
fi

echo "=== Development environment stopped ==="
