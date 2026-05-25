# E-Parking v2 — Go-Live Checklist

> **Date:** 26 April 2026
> **Version:** 2.0.0
> **Purpose:** Pre-deployment verification checklist for production deployment

---

## Pre-Deployment (1 Week Before)

### Business Readiness
- [ ] Legal entity registered (PT/CV)
- [ ] NPWP obtained
- [ ] NIB (Business ID) obtained
- [ ] Business bank account opened
- [ ] Domicile letter obtained
- [ ] Merchant agreement signed with acquirer
- [ ] MID/TID assigned
- [ ] Production init keys received
- [ ] SFTP/API credentials for settlement configured

### Hardware Readiness
- [ ] Production PASSTI readers with SAM modules ordered
- [ ] Controllers (Compass/ENET/Serial) installed and tested
- [ ] Cameras installed and configured
- [ ] Printers installed and tested
- [ ] Network infrastructure ready (VLANs, static IPs)
- [ ] Serial ports assigned and tested
- [ ] Backup hardware on-site (N+1 redundancy)

### Environment Setup
- [ ] Production server provisioned (Ubuntu 22.04 LTS)
- [ ] PostgreSQL 16+ installed and configured
- [ ] Redis 7+ installed and configured
- [ ] nginx installed and configured
- [ ] Python 3.12+ installed
- [ ] `parking` user created with `dialout` group
- [ ] SSL/TLS certificate obtained and installed
- [ ] DNS configured and propagated

---

## Deployment Day

### Pre-Flight Checks
Run the automated preflight check:
```bash
python scripts/preflight_check.py
```

Expected: All checks PASS or WARN (no FAIL)

### Manual Verification

#### 1. Infrastructure
- [ ] Server reboots successfully
- [ ] All services start automatically (`systemctl is-system-running`)
- [ ] Disk space > 20% free
- [ ] Memory usage < 80%
- [ ] Load average < number of CPU cores

#### 2. Database
- [ ] PostgreSQL service running
- [ ] Alembic migrations applied (`alembic current` matches latest)
- [ ] Backup script tested (`scripts/backup.sh`)
- [ ] Backup restore tested on staging

#### 3. Redis
- [ ] Redis service running
- [ ] `redis-cli ping` returns PONG
- [ ] Memory usage < 70%
- [ ] Persistence enabled (AOF or RDB)

#### 4. Application
- [ ] FastAPI starts without errors
- [ ] Health endpoint returns `{"status": "ok"}`
- [ ] Detailed health shows DB + Redis OK
- [ ] Metrics endpoint returns Prometheus format
- [ ] All 71 routes loaded
- [ ] Security headers present (`curl -I /api/health`)
- [ ] Rate limiting active (`curl -I /api/auth/login` — check headers)

#### 5. Frontend
- [ ] Nuxt build completes without errors
- [ ] Static files served by nginx
- [ ] Login page accessible
- [ ] All pages load without 404s

#### 6. Workers
- [ ] Critical worker starts (`arq workers.settings.CriticalWorkerSettings`)
- [ ] Background worker starts (`arq workers.settings.BackgroundWorkerSettings`)
- [ ] Worker queues visible in Redis (`redis-cli KEYS arq:queue:*`)

#### 7. Gate Daemons
- [ ] Gate-in daemon connects to controller
- [ ] Gate-out daemon connects to controller
- [ ] Heartbeat events published every 30s
- [ ] Redis consumer groups created (`XINFO GROUPS parking.commands.*`)

#### 8. Booth Bridge (per booth PC)
- [ ] Booth bridge service running (`systemctl status booth-bridge`)
- [ ] Serial devices detected (`ls -la /dev/ttyUSB*`)
- [ ] WebSocket accepts connections on localhost:5678
- [ ] POS page auto-detects booth by IP
- [ ] POS locks to assigned gate (dropdown hidden for operators)

#### 9. Hardware Integration
- [ ] Controller responds to STAT command
- [ ] PASSTI reader responds to INIT (via booth bridge)
- [ ] Printer prints test ticket (via booth bridge)
- [ ] Barcode scanner inputs to POS field
- [ ] Camera captures test snapshot
- [ ] Gate opens/closes via daemon command

#### 9. Payment Flows
- [ ] Cash payment end-to-end (entry → exit → cash → gate opens)
- [ ] RFID member payment end-to-end
- [ ] E-money payment end-to-end
- [ ] Timeout alert triggers correctly
- [ ] Manual override works

#### 10. Settlement
- [ ] Settlement directory writable
- [ ] Test settlement file generated
- [ ] File format matches Multibank v1.3 spec
- [ ] SFTP upload test successful (sandbox)

---

## Post-Deployment (First 24 Hours)

### Monitoring
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboards accessible
- [ ] Alertmanager configured
- [ ] Log aggregation working (JSON logs → Loki/ELK)
- [ ] Error rate < 1%
- [ ] API P95 latency < 500ms
- [ ] Payment success rate > 99%

### Validation
- [ ] First real transaction recorded in database
- [ ] First snapshot saved to disk
- [ ] First receipt printed
- [ ] First settlement file generated
- [ ] Backup completed successfully

### Communication
- [ ] Operations team notified of deployment
- [ ] Parking attendants trained on system
- [ ] Emergency contact list distributed
- [ ] On-call engineer assigned

---

## Rollback Plan

If critical issues are detected within 24 hours of deployment:

### Immediate Actions (0-5 minutes)
1. Stop all gate daemons to prevent incorrect transactions
2. Switch gates to manual mode
3. Notify operations team

### Short-Term (5-30 minutes)
1. Identify root cause from logs
2. If fix is simple: apply hotfix
3. If fix is complex: initiate rollback

### Rollback Procedure
```bash
# 1. Stop services
sudo systemctl stop parking-api parking-worker-critical parking-worker-snapshot parking-worker-bg
sudo systemctl stop 'parking-daemon-gate-in@*'
sudo systemctl stop booth-bridge   # exit lanes (no gate-out daemon)

# 2. Restore database from pre-deployment backup
gunzip < /backup/parking_YYYYMMDD_HHMMSS.sql.gz | psql -U parking -d parking

# 3. Checkout previous git tag
cd /opt/parking-system-v2
git checkout <previous-tag>

# 4. Reinstall dependencies
source .venv/bin/activate
pip install -e ".[dev]"

# 5. Restart services
sudo systemctl start parking-api parking-worker-critical parking-worker-bg
```

### Post-Rollback
1. Verify system functionality
2. Document rollback reason
3. Schedule root cause analysis
4. Plan corrected deployment

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Manager | ___________ | ___________ | _______ |
| Tech Lead | ___________ | ___________ | _______ |
| DevOps Engineer | ___________ | ___________ | _______ |
| Security Lead | ___________ | ___________ | _______ |
| Operations Manager | ___________ | ___________ | _______ |
| QA Lead | ___________ | ___________ | _______ |

---

*This checklist must be completed before any production deployment. Keep this document with the deployment records.*
