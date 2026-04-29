#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="eparking-dev"

echo "=== E-Parking v2 tmux Development Session ==="

# Check if tmux is installed
if ! command -v tmux &>/dev/null; then
    echo "ERROR: tmux is not installed. Install with: sudo apt install tmux"
    exit 1
fi

# Kill existing session if any
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Start infrastructure first
cd "$PROJECT_ROOT"
docker compose up -d postgres redis pgbouncer

# Create session with first pane: Docker logs
tmux new-session -d -s "$SESSION" -n "infra" \
    "cd $PROJECT_ROOT && echo '=== Docker Infrastructure Logs ===' && docker compose logs -f"

# Split horizontally: Pane 2 = API
tmux split-window -h -t "$SESSION:infra" \
    "cd $PROJECT_ROOT && source .venv/bin/activate && alembic upgrade head && uvicorn api.app.main:app --reload --host 0.0.0.0 --port 8000"

# Split vertically from the new pane: Pane 3 = Frontend
tmux split-window -v -t "$SESSION:infra" \
    "cd $PROJECT_ROOT/frontend && echo '=== Frontend Dev Server ===' && npm run dev"

# Split vertically again: Pane 4 = Daemon placeholder
tmux split-window -v -t "$SESSION:infra" \
    "cd $PROJECT_ROOT && echo '=== Gate Daemon Shell ===' && echo 'Run: python -m daemons.gate_in --gate-id <id>' && echo 'Run: python -m daemons.gate_out --gate-id <id>' && bash"

# Arrange in 2x2 grid
tmux select-layout -t "$SESSION:infra" tiled

# Attach
echo "Attaching to tmux session '$SESSION'..."
echo "  Detach with: Ctrl+B then D"
echo "  Kill with:   tmux kill-session -t $SESSION"
tmux attach -t "$SESSION"
