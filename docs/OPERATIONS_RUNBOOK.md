# E-Parking v2 — Operations Runbook

> **Version:** 2.0.0
> **Last Updated:** 26 April 2026

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Deployment](#deployment)
3. [Daily Operations](#daily-operations)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Troubleshooting](#troubleshooting)
6. [Backup & Recovery](#backup--recovery)
7. [Security](#security)
8. [Emergency Procedures](#emergency-procedures)

---

## System Overview

### Architecture

```
Nuxt 3 SPA (Element Plus + Pinia)
      |
      | HTTP/REST + WebSocket
      v
FastAPI Backend (Gunicorn + Uvicorn)
      |
      +-- PostgreSQL (data)
      +-- Redis (caching, IPC, rate limiting)
      |
      +-- ARQ Critical Worker (print, snapshot)
      +-- ARQ Background Worker (settlement, cleanup, notifications)
      |
      +-- Gate-In Daemons (one per gate)
      +-- Gate-Out Daemons (one per gate)
```

### Service Inventory

| Service | systemd Unit | User | Purpose |
|---------|-------------|------|---------|
| API | `parking-api.service` | `parking` | FastAPI HTTP/WebSocket server |
| Critical Worker | `parking-worker-critical.service` | `parking` | Print jobs, snapshots |
| Background Worker | `parking-worker-bg.service` | `parking` | Settlement, cleanup, alerts |
| Gate-In Daemon | `parking-daemon-gate-in@{id}.service` | `parking` | Entry gate control |
| Gate-Out Daemon | `parking-daemon-gate-out@{id}.service` | `parking` | Exit gate control |
| Booth Bridge | `booth-bridge.service` | `parking` | Serial device WebSocket bridge |
| PostgreSQL | `postgresql.service` | `postgres` | Database |
| Redis | `redis-server.service` | `redis` | Cache + message broker |
| Nginx | `nginx.service` | `root` | Reverse proxy + static files |

### Multi-PC Architecture

For installations with multiple gate-outs (booths), see the dedicated [Booth Deployment Guide](BOOTH_DEPLOYMENT.md). The typical setup is:

- **Server PC**: API, database, Redis, frontend, optionally Booth 1
- **Booth PC 2..N**: Booth bridge + Chrome POS for additional gate-outs

Each booth PC runs `booth-bridge.service` to expose its local serial devices (e-money reader, receipt printer, barcode scanner) via WebSocket to the POS web app.

---

## Deployment

### Prerequisites

- Ubuntu 22.04 LTS or compatible
- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- nginx
- `ffmpeg` (for RTSP camera support)

### Initial Setup

```bash
# 1. Create user
sudo useradd -r -s /bin/false parking
sudo usermod -aG dialout parking  # Serial access

# 2. Clone repository
cd /opt
sudo git clone <repo-url> parking-system-v2
sudo chown -R parking:parking parking-system-v2

# 3. Create virtual environment
cd parking-system-v2
sudo -u parking python3 -m venv .venv
sudo -u parking .venv/bin/pip install -e ".[dev]"

# 4. Configure environment
sudo -u parking cp .env.example .env
sudo -u parking nano .env  # Edit all required values

# 5. Create snapshot directory
sudo mkdir -p /var/lib/parking/snapshots
sudo chown -R parking:parking /var/lib/parking

# 6. Run database migrations
sudo -u parking .venv/bin/alembic upgrade head

# 7. Seed initial data (optional)
sudo -u parking .venv/bin/python scripts/seed.py

# 8. Build frontend
cd frontend
npm install
npm run build
cd ..

# 9. Copy systemd services
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# 10. Start core services
sudo systemctl enable --now parking-api parking-worker-critical parking-worker-bg

# 11. Start gate daemons (one per gate)
sudo systemctl enable --now parking-daemon-gate-in@gate-in-1
sudo systemctl enable --now parking-daemon-gate-out@gate-out-1
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `JWT_SECRET` | Yes | 64+ character random string |
| `APP_ENV` | Yes | `production` or `development` |
| `SETTLEMENT_DIR` | Yes | Path for settlement files |
| `TELEGRAM_BOT_TOKEN` | No | For alerts |
| `TELEGRAM_CHAT_ID` | No | For alerts |

---

## Daily Operations

### Settlement Upload

**Automated (default):**
- Background worker generates settlement files at configured schedule
- Files are written to `SETTLEMENT_DIR`
- Upload to acquirer SFTP (requires production credentials)

**Manual trigger:**
```bash
# Via API
curl -X POST https://parking.example.com/api/settlements/trigger \
  -H "Cookie: access_token=<token>"
```

### Backup

**Database:**
```bash
#!/bin/bash
# /opt/parking-system-v2/scripts/backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U parking -h localhost parking | gzip > /backup/parking_${DATE}.sql.gz
find /backup -name "parking_*.sql.gz" -mtime +7 -delete
```

**Snapshots:**
```bash
rsync -av /var/lib/parking/snapshots/ /backup/snapshots/
```

**Settlement files:**
```bash
rsync -av /var/lib/parking/settlements/ /backup/settlements/
```

### Log Rotation

```bash
# /etc/logrotate.d/parking
/var/log/parking/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 parking parking
}
```

---

## Monitoring & Alerting

### Health Checks

```bash
# Basic health
curl https://parking.example.com/api/health
# -> {"status": "ok"}

# Detailed health (DB + Redis connectivity)
curl "https://parking.example.com/api/health?detailed=true"
# -> {"status": "ok", "database": "ok", "redis": "ok"}
# -> {"status": "degraded", "database": "error", "redis": "ok"}
```

### Prometheus Metrics

```bash
curl https://parking.example.com/metrics
```

Key metrics:
- `http_requests_total` — HTTP request counter
- `http_request_duration_seconds` — Latency histogram
- `payment_attempts_total` — Payment attempts by method
- `payment_success_total` — Successful payments by method
- `parking_settlements_total` — Settlement file generation

### Critical Alerts

| Condition | Severity | Action |
|-----------|----------|--------|
| Database down | Critical | Check PostgreSQL service, disk space |
| Redis down | Critical | Check Redis service, memory |
| Daemon heartbeat missing > 60s | Critical | Restart daemon, check hardware |
| Payment failure rate > 10% | Warning | Check e-money reader, network |
| Settlement file not generated | Warning | Trigger manual generation |
| Disk usage > 90% | Warning | Clean old snapshots/logs |

---

## Troubleshooting

### Gate Not Opening

1. Check daemon status: `sudo systemctl status parking-daemon-gate-out@gate-out-1`
2. Check daemon logs: `sudo journalctl -u parking-daemon-gate-out@gate-out-1 -f`
3. Test controller connectivity: `python scripts/controller_test.py compass <ip>`
4. Verify Redis Streams: `redis-cli XINFO GROUPS parking.commands.gate-out-1`

### E-Money Reader Not Responding

1. Check reader power and serial cable
2. Verify booth bridge is running: `sudo systemctl status booth-bridge`
3. Check serial device path in `/etc/parking/booth.json`
4. Run diagnostic: `python scripts/emoney_diagnostic.py`
5. Verify init key is correct
6. Check for SAM module errors in logs: `sudo journalctl -u booth-bridge -f`

### Booth Bridge Issues

1. Check service status: `sudo systemctl status booth-bridge`
2. Verify config: `cat /etc/parking/booth.json`
3. Check serial permissions: `ls -la /dev/ttyUSB*` (should be `dialout` group)
4. Test WebSocket: `curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:5678/`
5. Review logs: `sudo journalctl -u booth-bridge -n 50`

### Payment Timeout

1. Check POS WebSocket connection to API
2. Check booth bridge WebSocket connection (`localhost:5678`)
3. Verify operator has correct gate selected (or auto-detected)
4. Check network latency between POS and API
5. Review `timeout_alert` events in notification page

### Database Connection Errors

1. Check PostgreSQL: `sudo systemctl status postgresql`
2. Verify connection string in `.env`
3. Check connection pool usage
4. Review PostgreSQL logs: `/var/log/postgresql/`

### High Memory Usage

1. Check for memory leaks in daemons: `ps aux --sort=-%mem | head`
2. Restart services if needed
3. Verify snapshot cleanup worker is running
4. Check Redis memory: `redis-cli INFO memory`

---

## Backup & Recovery

### Restore Database

```bash
# Stop API and workers
sudo systemctl stop parking-api parking-worker-critical parking-worker-bg

# Restore from backup
gunzip < /backup/parking_20260426_000000.sql.gz | psql -U parking -d parking

# Start services
sudo systemctl start parking-api parking-worker-critical parking-worker-bg
```

### Disaster Recovery

1. **Provision new server** with same OS
2. **Restore database** from latest backup
3. **Clone application** and install dependencies
4. **Copy `.env`** and settlement files
5. **Start services** in order: PostgreSQL → Redis → API → Workers → Daemons
6. **Verify** with health checks and test transactions

---

## Security

### Secrets Management

- **Never commit `.env` to version control**
- Rotate `JWT_SECRET` quarterly
- Store production init keys in hardware security module or encrypted vault
- Use environment variables for all sensitive configuration

### Network Security

- API should be behind nginx with TLS 1.3
- Controller networks should be isolated (VLAN)
- RTSP streams should use authentication
- Redis should bind to localhost only

### Access Control

| Role | Permissions |
|------|-------------|
| admin | All operations, settings, user management |
| operator | POS, transactions, member lookup |
| supervisor | Reports, manual overrides |

### Audit Review

```bash
# Review recent payments
psql -U parking -d parking -c "SELECT * FROM audit_logs WHERE action LIKE '%PAYMENT%' ORDER BY created_at DESC LIMIT 20;"

# Review manual gate opens
psql -U parking -d parking -c "SELECT * FROM audit_logs WHERE action = 'MANUAL_GATE_OPEN' ORDER BY created_at DESC LIMIT 20;"
```

---

## Emergency Procedures

### Complete System Failure

1. **Switch to manual mode**: Open all gates manually
2. **Notify management**: Use backup communication
3. **Collect paper records**: Note all transactions manually
4. **Restart services**: Follow recovery procedure
5. **Reconcile transactions**: Compare paper vs system records

### Data Corruption

1. **Stop all writes**: Stop API and workers
2. **Assess damage**: Identify corrupted tables
3. **Restore from backup**: Use most recent clean backup
4. **Re-run settlements**: Generate missing settlement files
5. **Verify integrity**: Run full test suite

### Security Breach

1. **Revoke all sessions**: Clear Redis denylist, rotate JWT secret
2. **Audit all actions**: Review audit_logs for suspicious activity
3. **Change all passwords**: Force password reset for all users
4. **Review access logs**: Check nginx access logs
5. **Report incident**: Follow organizational security policy

---

## Contact Information

| Role | Contact | Purpose |
|------|---------|---------|
| System Administrator | _______________ | Infrastructure issues |
| Parking Operations | _______________ | Business/day-to-day issues |
| PT Softorb | +62 21 29668601 | Hardware support |
| Acquirer (Luminos/etc) | _______________ | Settlement issues |

---

*This runbook should be reviewed and updated quarterly.*
