# Security Headers Middleware

> 23 nodes · cohesion 0.09

## Key Concepts

- **TestSecurityHeadersMiddleware** (13 connections) — `api/tests/test_security_headers.py`
- **SecurityHeadersMiddleware** (6 connections) — `api/app/middleware/security_headers.py`
- **test_security_headers.py** (3 connections) — `api/tests/test_security_headers.py`
- **security_headers.py** (2 connections) — `api/app/middleware/security_headers.py`
- **BaseHTTPMiddleware** (2 connections)
- **.test_health_endpoint_has_headers()** (2 connections) — `api/tests/test_security_headers.py`
- **Security headers middleware for FastAPI.  Adds defense-in-depth security headers** (1 connections) — `api/app/middleware/security_headers.py`
- **Middleware that adds security headers to all responses.      Headers added:** (1 connections) — `api/app/middleware/security_headers.py`
- **.dispatch()** (1 connections) — `api/app/middleware/security_headers.py`
- **.__init__()** (1 connections) — `api/app/middleware/security_headers.py`
- **client()** (1 connections) — `api/tests/test_security_headers.py`
- **Tests for security headers middleware.** (1 connections) — `api/tests/test_security_headers.py`
- **Test suite for security headers middleware.** (1 connections) — `api/tests/test_security_headers.py`
- **Security headers should be present even on public health endpoints.** (1 connections) — `api/tests/test_security_headers.py`
- **.test_content_security_policy()** (1 connections) — `api/tests/test_security_headers.py`
- **.test_custom_csp()** (1 connections) — `api/tests/test_security_headers.py`
- **.test_hsts_disabled_by_default()** (1 connections) — `api/tests/test_security_headers.py`
- **.test_hsts_when_enabled()** (1 connections) — `api/tests/test_security_headers.py`
- **.test_permissions_policy()** (1 connections) — `api/tests/test_security_headers.py`
- **.test_referrer_policy()** (1 connections) — `api/tests/test_security_headers.py`
- **.test_response_body_unchanged()** (1 connections) — `api/tests/test_security_headers.py`
- **.test_x_content_type_options()** (1 connections) — `api/tests/test_security_headers.py`
- **.test_x_frame_options()** (1 connections) — `api/tests/test_security_headers.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/app/middleware/security_headers.py`
- `api/tests/test_security_headers.py`

## Audit Trail

- EXTRACTED: 43 (96%)
- INFERRED: 2 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*