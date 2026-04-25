#!/bin/bash
set -euo pipefail

# E-Parking System v2 Deployment Script
# Usage: ./scripts/deploy.sh

APP_DIR="/opt/parking-system-v2"
FRONTEND_DIR="/var/www/parking-frontend"
USER="parking"

echo "=== E-Parking v2 Deployment ==="

# 1. Build frontend
echo "[1/6] Building frontend..."
cd "$APP_DIR/frontend"
npm install
npm run build

# 2. Copy frontend to web root
echo "[2/6] Copying frontend build..."
mkdir -p "$FRONTEND_DIR"
cp -r "$APP_DIR/frontend/.output/public/"* "$FRONTEND_DIR/"

# 3. Update Python dependencies
echo "[3/6] Updating Python dependencies..."
cd "$APP_DIR"
source .venv/bin/activate
pip install -e ".[dev]"

# 4. Run database migrations
echo "[4/6] Running database migrations..."
cd "$APP_DIR/api"
alembic upgrade head

# 5. Copy nginx config
echo "[5/6] Updating nginx configuration..."
sudo cp "$APP_DIR/docker/nginx.conf" /etc/nginx/sites-available/parking
sudo nginx -t && sudo systemctl reload nginx

# 6. Restart services
echo "[6/6] Restarting services..."
sudo systemctl daemon-reload
sudo systemctl restart parking-api
sudo systemctl restart parking-worker-critical
sudo systemctl restart parking-worker-bg

# Restart gate daemons (if any are enabled)
for service in $(systemctl list-units --plain --no-legend 'parking-daemon-gate-in@*'); do
    sudo systemctl restart "$service"
done
for service in $(systemctl list-units --plain --no-legend 'parking-daemon-gate-out@*'); do
    sudo systemctl restart "$service"
done

# Health check
echo "=== Health Check ==="
sleep 2
curl -sf http://localhost/api/health && echo "API OK" || echo "API FAIL"

echo "=== Deployment Complete ==="
