# JWT Authentication

> 25 nodes · cohesion 0.12

## Key Concepts

- **create_access_token()** (9 connections) — `api/app/utils/jwt.py`
- **decode_token()** (9 connections) — `api/app/utils/jwt.py`
- **test_jwt.py** (7 connections) — `api/tests/test_jwt.py`
- **create_refresh_token()** (7 connections) — `api/app/utils/jwt.py`
- **jwt.py** (6 connections) — `api/app/utils/jwt.py`
- **test_access_refresh_different()** (5 connections) — `api/tests/test_jwt.py`
- **test_token_expiry()** (4 connections) — `api/tests/test_jwt.py`
- **_now()** (4 connections) — `api/app/utils/jwt.py`
- **test_create_access_token()** (3 connections) — `api/tests/test_jwt.py`
- **test_create_refresh_token()** (3 connections) — `api/tests/test_jwt.py`
- **test_decode_invalid_token()** (3 connections) — `api/tests/test_jwt.py`
- **test_decode_token()** (3 connections) — `api/tests/test_jwt.py`
- **get_token_expiry()** (3 connections) — `api/app/utils/jwt.py`
- **Tests for JWT utilities.** (1 connections) — `api/tests/test_jwt.py`
- **Test access token creation.** (1 connections) — `api/tests/test_jwt.py`
- **Test refresh token creation.** (1 connections) — `api/tests/test_jwt.py`
- **Test token has expiry.** (1 connections) — `api/tests/test_jwt.py`
- **Test decoding invalid token raises exception.** (1 connections) — `api/tests/test_jwt.py`
- **Test access and refresh tokens are different.** (1 connections) — `api/tests/test_jwt.py`
- **JWT token utilities using PyJWT.** (1 connections) — `api/app/utils/jwt.py`
- **Return current UTC time.** (1 connections) — `api/app/utils/jwt.py`
- **Create a short-lived JWT access token.** (1 connections) — `api/app/utils/jwt.py`
- **Create a long-lived JWT refresh token.** (1 connections) — `api/app/utils/jwt.py`
- **Decode and validate a JWT token.** (1 connections) — `api/app/utils/jwt.py`
- **Extract expiry timestamp from token without full validation.** (1 connections) — `api/app/utils/jwt.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `api/app/utils/jwt.py`
- `api/tests/test_jwt.py`

## Audit Trail

- EXTRACTED: 50 (64%)
- INFERRED: 28 (36%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*