# E-Parking v2 — On-Call Runbook

> **Date:** 26 April 2026
> **Version:** 2.0.0
> **Audience:** System administrators, on-call engineers

---

## 1. On-Call Structure

### Escalation Path
```
Level 1: On-call Engineer (primary responder)
    ↓ (5 minutes, no ACK)
Level 2: Senior Engineer
    ↓ (10 minutes, no ACK)
Level 3: Engineering Manager
    ↓ (15 minutes, no ACK)
Level 4: CTO / VP Engineering
```

### Rotation
- Weekly rotation, Monday 00:00 to Sunday 23:59
- Handoff meeting every Monday 09:00
- On-call calendar in shared calendar system

---

## 2. Alert Severity Levels

### P1 — Critical (Wake-up Call)
| Condition | Response Time | Action |
|-----------|---------------|--------|
| Database down | 5 min | Immediate response required |
| Redis down | 5 min | Immediate response required |
| All gates offline | 5 min | Immediate response required |
| Payment failure rate > 50% | 5 min | Immediate response required |
| Settlement not uploaded > 24h | 5 min | Immediate response required |

### P2 — High (Business Hours)
| Condition | Response Time | Action |
|-----------|---------------|--------|
| Single gate offline | 15 min | Respond within 15 min |
| Payment failure rate 10-50% | 15 min | Respond within 15 min |
| Disk usage > 90% | 30 min | Respond within 30 min |
| Memory usage > 90% | 30 min | Respond within 30 min |
| Daemon heartbeat missing > 60s | 15 min | Respond within 15 min |

### P3 — Medium (Next Business Day)
| Condition | Response Time | Action |
|-----------|---------------|--------|
| Settlement file not generated | 4 hours | Respond same day |
| Backup failure | 4 hours | Respond same day |
| High API latency (> 2s P95) | 4 hours | Respond same day |
| Certificate expiring < 30 days | 24 hours | Respond within 24h |

### P4 — Low (Next Sprint)
| Condition | Response Time | Action |
|-----------|---------------|--------|
| Non-critical log errors | 1 week | Track and plan fix |
| Dependency updates available | 1 week | Schedule maintenance |

---

## 3. Response Playbooks

### P1: Database Down

**Symptoms:**
- `/api/health?detailed=true` returns `database: error`
- All payment endpoints return 500
- Operator complaints

**Diagnosis:**
```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Check logs
sudo journalctl -u postgresql -n 50

# Check disk space
df -h

# Check connection
sudo -u postgres psql -c "SELECT 1"
```

**Resolution:**
1. If service stopped: `sudo systemctl start postgresql`
2. If disk full: free space, restart PostgreSQL
3. If corrupted: restore from backup (see OPERATIONS_RUNBOOK.md)
4. If hardware failure: failover to standby (if configured)

**Communication:**
- Post in #incidents channel immediately
- Update status page
- Notify parking operations manager

---

### P1: Redis Down

**Symptoms:**
- `/api/health?detailed=true` returns `redis: error`
- Rate limiting fails open (no protection)
- WebSocket broadcasting may fail
- Session management degraded

**Diagnosis:**
```bash
sudo systemctl status redis-server
sudo journalctl -u redis-server -n 50
redis-cli ping
```

**Resolution:**
1. Restart Redis: `sudo systemctl restart redis-server`
2. Check memory: `redis-cli INFO memory`
3. If OOM: increase memory or flush old data

---

### P1: All Gates Offline

**Symptoms:**
- No heartbeat events from any daemon
- Operators report gates not responding

**Diagnosis:**
```bash
# Check all daemon services
sudo systemctl status 'parking-daemon-*'

# Check Redis Streams
redis-cli XINFO STREAMS parking.commands.*

# Check network to controllers
for ip in 192.168.1.100 192.168.1.101; do
    ping -c 1 $ip
done
```

**Resolution:**
1. If network issue: contact network admin
2. If daemon crash: check logs, restart services
3. If controller failure: switch to manual mode

---

### P2: Single Gate Offline

**Diagnosis:**
```bash
# Check specific daemon
sudo systemctl status parking-daemon-gate-out@gate-out-1
sudo journalctl -u parking-daemon-gate-out@gate-out-1 -f

# Test controller connectivity
python scripts/hardware/controller_diagnostic.py <ip> <port>
```

**Resolution:**
1. Restart daemon: `sudo systemctl restart parking-daemon-gate-out@gate-out-1`
2. If controller unresponsive: check power/network
3. If hardware failure: dispatch technician

---

### P2: High Payment Failure Rate

**Diagnosis:**
```bash
# Check metrics
curl -s http://localhost/metrics | grep payment_success_total

# Check e-money reader logs
sudo journalctl -u parking-daemon-gate-out@gate-out-1 | grep -i "passti\|reader\|error"

# Run diagnostic
python scripts/hardware/passti_diagnostic.py /dev/ttyUSB0
```

**Resolution:**
1. If e-money reader issue: restart reader, check serial cable
2. If network issue: check API connectivity
3. If member validation slow: check Redis cache

---

## 4. Monitoring Dashboard

### Key Metrics to Watch

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| API P95 latency | < 200ms | 200-500ms | > 500ms |
| DB connections | < 80% pool | 80-95% | > 95% |
| Redis memory | < 70% | 70-90% | > 90% |
| Daemon heartbeat | < 35s | 35-60s | > 60s |
| Payment success rate | > 99% | 95-99% | < 95% |
| Settlement upload | On time | < 2h delay | > 2h delay |

### Dashboard URLs
- **Grafana**: http://monitoring.internal/grafana (import dashboard JSON)
- **Prometheus**: http://monitoring.internal:9090
- **Alertmanager**: http://monitoring.internal:9093

---

## 5. Tools & Access

### Required Access
| System | Access Method | Credentials Location |
|--------|--------------|---------------------|
| Production servers | SSH key | Password manager |
| Database | psql + SSH tunnel | Password manager |
| Redis | redis-cli + SSH tunnel | Password manager |
| Monitoring | Web UI | SSO |
| Cloud provider | Console | SSO |

### Useful Commands
```bash
# Quick health check
curl -s http://localhost/api/health | jq .

# Check all services
sudo systemctl status parking-api parking-worker-critical parking-worker-bg

# View recent errors
sudo journalctl -u parking-api --since "1 hour ago" | grep -i error

# Database query
sudo -u postgres psql -d parking -c "SELECT COUNT(*) FROM parking_transactions WHERE status = 'active';"

# Redis inspection
redis-cli INFO clients
redis-cli XINFO GROUPS parking.commands.gate-out-1

# Disk cleanup
sudo find /var/log/parking -name "*.log" -mtime +30 -delete
```

---

## 6. Incident Communication

### Internal Communication
1. **Acknowledge** alert within SLA time
2. **Create incident** in incident management system
3. **Update** #incidents channel with status
4. **Resolve** and post-mortem within 48 hours

### External Communication
- Parking operations: via Telegram/phone
- Public status page: update for extended outages
- Acquirer: notify if settlement affected

### Incident Template
```
Incident: [P1/P2/P3/P4] Brief description
Started: YYYY-MM-DD HH:MM
Impact: [e.g., "All exit gates at Location X"]
Status: [Investigating / Identified / Monitoring / Resolved]

Updates:
- HH:MM — [Update]

Resolution:
- HH:MM — [What fixed it]
```

---

## 7. Post-Incident Review

### Required for P1/P2
Within 48 hours of resolution:

1. **Timeline** — What happened, when
2. **Root cause** — 5 Whys analysis
3. **Impact** — Duration, affected transactions, revenue loss
4. **Resolution** — How it was fixed
5. **Prevention** — Action items to prevent recurrence
6. **Follow-up** — Tickets created, owners assigned

### Template
```markdown
# Post-Incident Review: [Incident ID]

## Timeline
- HH:MM — Alert fired
- HH:MM — Engineer acknowledged
- HH:MM — Root cause identified
- HH:MM — Fix applied
- HH:MM — Resolved

## Root Cause
[Explanation]

## Impact
- Duration: X minutes
- Transactions affected: Y
- Revenue impact: Z

## Action Items
- [ ] [Action] — Owner: [Name] — Due: [Date]
```

---

## 8. Contact Information

| Role | Name | Phone | Slack |
|------|------|-------|-------|
| On-call Engineer | ___________ | ___________ | @oncall |
| Senior Engineer | ___________ | ___________ | @senior-eng |
| Engineering Manager | ___________ | ___________ | @eng-manager |
| CTO | ___________ | ___________ | @cto |
| Parking Operations | ___________ | ___________ | @ops |
| PT Softorb (Hardware) | +62 21 29668601 | — | — |
| Acquirer Support | ___________ | ___________ | — |

---

*This runbook should be reviewed and updated after every P1/P2 incident.*
