# E-Parking v2 — Security Review

> **Date:** 26 April 2026
> **Version:** 2.0.0
> **Scope:** Final security review before production deployment

---

## 1. Authentication & Authorization

### JWT Implementation
| Aspect | Status | Notes |
|--------|--------|-------|
| Algorithm | HS256 | OK for single-server deployments. RS256 recommended for multi-service. |
| Token storage | httpOnly cookies | ✅ Secure — inaccessible to JavaScript |
| Token expiry | Access: 30min, Refresh: 7d | ✅ Short-lived access tokens reduce blast radius |
| Token revocation | Redis denylist | ✅ O(1) check, TTL auto-cleanup |
| Secret management | Environment variable | ⚠️ Must be 64+ chars in production |
| Cookie flags | Secure, SameSite | ⚠️ Enable `Secure` flag when HTTPS is deployed |

### Role-Based Access Control
| Role | Permissions | Enforcement |
|------|-------------|-------------|
| admin | All operations | `require_admin` dependency |
| operator | POS, transactions, member lookup | `require_operator` dependency |
| supervisor | Reports, manual overrides | `require_operator` dependency (shared) |

**Review finding:** All admin routes correctly use `require_admin`. All operator routes use `require_operator`. No unprotected admin endpoints found.

---

## 2. Input Validation

### Validation Layers
| Layer | Implementation | Coverage |
|-------|---------------|----------|
| Pydantic schemas | `api/app/schemas/` | All request bodies |
| Path parameters | FastAPI native | All route parameters |
| Query parameters | `PaginationParams` dependency | All list endpoints |
| Database constraints | SQLAlchemy + PostgreSQL | Unique indexes, check constraints |

### Key Validations
- `uq_active_card`: Prevents duplicate active transactions per card number
- `GateOut.payment_timeout_seconds`: Must be >= 10 seconds
- `EmoneyReader.init_key`: Encrypted at rest (application layer)
- Barcode format: CODE39, 5 characters

---

## 3. Secrets Management

### Secrets Inventory
| Secret | Storage | Rotation | Risk |
|--------|---------|----------|------|
| JWT_SECRET | `.env` / env var | Quarterly | HIGH — compromise = full auth bypass |
| DB_PASSWORD | `.env` / env var | Quarterly | HIGH — compromise = data breach |
| REDIS_URL | `.env` / env var | On compromise | MEDIUM — session theft |
| PASSTI init key | `EmoneyReader` table, encrypted | Per acquirer policy | CRITICAL — money flow |
| Telegram bot token | `.env` / env var | On compromise | LOW — alert only |

### Recommendations
1. **Use a secrets manager** (HashiCorp Vault, AWS Secrets Manager) for production
2. **Never commit `.env` to git** — verified in `.gitignore`
3. **Rotate JWT_SECRET quarterly** — document procedure in runbook
4. **Encrypt PASSTI init keys** with KMS before storing in DB

---

## 4. Network Security

### Current Configuration
| Component | Binding | Notes |
|-----------|---------|-------|
| API (Gunicorn) | 127.0.0.1:8000 | ✅ Not exposed directly |
| PostgreSQL | 127.0.0.1:5432 | ✅ Localhost only in Docker |
| Redis | 127.0.0.1:6379 | ✅ Localhost only in Docker |
| nginx | 0.0.0.0:80 | Frontend + API proxy |

### nginx Security Headers
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
```

### FastAPI Security Headers (Week 12 addition)
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'; ...
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), ...
```

---

## 5. Audit Logging

### Coverage
| Action | Logged | Fields |
|--------|--------|--------|
| CASH_PAYMENT | ✅ | fee, transaction_id, operator |
| RFID_PAYMENT | ✅ | fee, transaction_id, operator |
| EMONEY_PAYMENT | ✅ | fee, amount_deducted, operator |
| MANUAL_GATE_OPEN | ✅ | gate_id, reason, operator |
| RESET_GATE | ✅ | gate_id, reason, operator |
| SETTING_UPDATE | ✅ | key, old_value, new_value |
| USER_CREATE/UPDATE/DELETE | ✅ | target_user_id, role |

### Audit Log Schema
```sql
audit_logs: id, user_id, username, action, entity_type, entity_id,
           details(JSONB), ip_address, user_agent, created_at
```

**Review finding:** No FK from audit_logs.user_id to users.id. This ensures audit records survive user deletion. ✅

---

## 6. Rate Limiting

### Configuration
| Path | Limit | Window |
|------|-------|--------|
| `/api/auth/login` | 5 | 60s |
| `/api/auth/refresh` | 10 | 60s |
| `/api/payments/*` | 30 | 60s |
| Fallback | 100 | 60s |

### Behavior
- Redis-backed sliding window
- Returns 429 with `Retry-After` header
- **Fail-open**: If Redis is down, requests are allowed
- Exempt paths: `/api/health`, `/metrics`, `/docs`, `/openapi.json`

---

## 7. Known Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| JWT secret compromised | Low | Critical | Quarterly rotation, 64+ char random string |
| Database breach | Low | Critical | Connection pooling, no plaintext passwords, encrypted init keys |
| Redis exposure | Low | High | Bind to localhost only, no AUTH in dev (add in prod) |
| Brute-force login | Medium | Medium | Rate limiting (5/min), account lockout TBD |
| Card data leakage | Low | Critical | No card PANs stored, only card numbers (not PCI-sensitive) |
| Settlement file tampering | Low | High | SHA256 hash stored, file permissions 0600 |
| Man-in-the-middle | Medium | High | TLS 1.3 in production (nginx config ready) |
| Insider threat | Medium | High | Audit logs, role separation, principle of least privilege |

### Risk Acceptance
- **Account lockout** after N failed logins: Not implemented. Mitigation: rate limiting + strong passwords.
- **2FA for admin accounts**: Not implemented. Mitigation: strong passwords + network isolation.
- **WAF (Web Application Firewall)**: Not implemented. Mitigation: input validation + rate limiting.

---

## 8. Dependency Security

### Scanning Tools
| Tool | Purpose | Command |
|------|---------|---------|
| `pip-audit` | Check PyPI packages for known CVEs | `pip-audit` |
| `safety check` | Alternative CVE scanner | `safety check` |
| `npm audit` | Check Node.js packages | `cd frontend && npm audit` |

### Current State
- Python dependencies: No known critical vulnerabilities (run `pip-audit` to verify)
- Node.js dependencies: 0 vulnerabilities as of Week 3 build

### Recommendations
1. Run `pip-audit` weekly in CI/CD
2. Pin all dependency versions in `pyproject.toml`
3. Subscribe to security advisories for FastAPI, SQLAlchemy, Redis

---

## 9. Production Checklist

Before going live, verify:

- [ ] JWT_SECRET is 64+ random characters
- [ ] `.env` is not in version control
- [ ] HTTPS/TLS 1.3 enabled in nginx
- [ ] `Secure` and `SameSite=Strict` flags on cookies
- [ ] PostgreSQL has strong password, not default
- [ ] Redis has `requirepass` enabled
- [ ] All services run as non-root user
- [ ] `parking` user is in `dialout` group
- [ ] Log rotation configured
- [ ] Backup scripts tested
- [ ] Monitoring alerts configured
- [ ] Incident response plan documented

---

## 10. Review Sign-off

| Reviewer | Date | Status |
|----------|------|--------|
| Security Lead | ___________ | ⬜ Approved / ⬜ Needs Changes |
| Dev Lead | ___________ | ⬜ Approved / ⬜ Needs Changes |
| Ops Lead | ___________ | ⬜ Approved / ⬜ Needs Changes |

---

*This document should be reviewed quarterly and after any security incident.*
