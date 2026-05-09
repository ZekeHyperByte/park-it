#!/usr/bin/env bash
# Daily PostgreSQL backup for E-Parking v2
# Called by systemd timer: parking-backup.timer
set -euo pipefail

# Load environment
if [ -f /opt/parking-system-v2/.env ]; then
    set -a
    source /opt/parking-system-v2/.env
    set +a
fi

BACKUP_DIR="${BACKUP_DIR:-/var/backups/parking}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-parking}"
DB_USER="${DB_USER:-parking}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/parking_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Starting backup: ${DB_NAME} -> ${BACKUP_FILE}"
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=6 \
    --verbose \
    -f "$BACKUP_FILE"

echo "Backup complete: $(du -h "$BACKUP_FILE" | cut -f1)"

# Clean up old backups
echo "Removing backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "parking_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

echo "Backup finished successfully"
