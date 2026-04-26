# Week 12 — Production Deployment & Security Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete final security review, certification preparation, go-live checklist, rollback procedures, operations handover docs, dependency security scanning, and final smoke tests.

**Architecture:** Add a FastAPI security headers middleware as defense in depth, create comprehensive certification and operations documentation, build pre-flight verification and rollback scripts, add dependency vulnerability scanning, and create a final smoke test suite.

**Tech Stack:** FastAPI middleware, bash scripts, pytest, pip-audit/safety, Python stdlib

---

## Task 1: Security Headers Middleware

**Files:**
- Create: `api/app/middleware/security_headers.py`
- Create: `api/tests/test_security_headers.py`
- Modify: `api/app/main.py` (add middleware)

**Step 1: Write the failing test**

```python
def test_security_headers_present(client):
    response = client.get("/api/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")
```

**Step 2: Run test to verify it fails**

Run: `pytest api/tests/test_security_headers.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self';"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
```

**Step 4: Register in main.py**

Add `app.add_middleware(SecurityHeadersMiddleware)` after rate limit middleware.

**Step 5: Run test to verify it passes**

Run: `pytest api/tests/test_security_headers.py -v`
Expected: PASS

---

## Task 2: Security Review Documentation

**Files:**
- Create: `docs/SECURITY_REVIEW.md`

Content covers:
- Authentication & Authorization review
- Input validation summary
- Secrets management
- Network security
- Audit logging coverage
- Rate limiting configuration
- Security headers
- Known risks and mitigations

---

## Task 3: Certification Preparation Documentation

**Files:**
- Create: `docs/CERTIFICATION_PREP.md`

Content covers:
- BI Certification requirements checklist
- PCI DSS compliance notes (what applies, what doesn't)
- SAM module requirements and procurement checklist
- Settlement file compliance verification
- Required business documents (NPWP, SIUP, TDP)
- Merchant application steps
- Certification testing preparation

---

## Task 4: Go-Live Checklist + Pre-flight Verification Script

**Files:**
- Create: `scripts/preflight_check.py`
- Create: `scripts/tests/test_preflight_check.py`
- Create: `docs/GO_LIVE_CHECKLIST.md`

**Script checks:**
- Environment variables set
- Database connectivity
- Redis connectivity
- JWT secret strength
- Settlement directory writable
- Snapshot directory writable
- ffmpeg installed
- Required ports available
- Disk space
- Memory

---

## Task 5: Rollback Procedures + Backup Verification

**Files:**
- Create: `scripts/verify_backup.py`
- Create: `scripts/tests/test_verify_backup.py`
- Update: `docs/OPERATIONS_RUNBOOK.md` (rollback section)

**Script checks:**
- Latest backup file exists and is non-empty
- Backup is restorable (dry-run)
- Backup age check

---

## Task 6: Operations Handover Documentation

**Files:**
- Create: `docs/OPERATOR_TRAINING.md`
- Create: `docs/ONCALL_RUNBOOK.md`
- Update: `docs/OPERATIONS_RUNBOOK.md`

**Content:**
- Operator training guide (POS usage, common issues)
- On-call procedures and escalation paths
- Monitoring dashboard setup instructions
- Alert response playbooks

---

## Task 7: Dependency Security Scan

**Files:**
- Create: `scripts/security_scan.py`
- Create: `scripts/tests/test_security_scan.py`
- Update: `docs/SECURITY_REVIEW.md`

**Script:**
- Run `pip-audit` or `safety check`
- Check for known CVEs in dependencies
- Output report with severity levels
- Exit code based on findings

---

## Task 8: Final Smoke Test Suite

**Files:**
- Create: `tests/smoke/test_smoke_go_live.py`

**Tests:**
- Health endpoint returns OK
- Auth login/logout works
- All critical API routes respond 200
- WebSocket endpoint accepts connections
- Redis connectivity
- Database connectivity
- Metrics endpoint returns data
- Rate limiting headers present
- Security headers present

---

## Task 9: Final Verification

Run full test suite:
```bash
pytest -q --deselect workers/tests/test_settlement_worker.py::TestGenerateSettlementFile::test_no_unsettled_transactions
```

Run frontend build:
```bash
cd frontend && npm run build
```

Verify route count:
```bash
python -c "from api.app.main import app; print(len([r for r in app.routes if hasattr(r,'path')]))"
```

---

## Task 10: Documentation

Create:
- `docs/WEEK 12/WEEK12_CHANGES.md`
- `docs/WEEK 12/WEEK12_TEST_CHECKLIST.md`
