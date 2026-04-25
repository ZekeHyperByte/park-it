"""JWT token utilities using PyJWT."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from shared.config import get_settings

settings = get_settings()


def _now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def create_access_token(data: dict[str, Any]) -> str:
    """Create a short-lived JWT access token."""
    to_encode = data.copy()
    expire = _now() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a long-lived JWT refresh token."""
    to_encode = data.copy()
    expire = _now() + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )


def get_token_expiry(token: str) -> datetime:
    """Extract expiry timestamp from token without full validation."""
    payload = jwt.decode(
        token,
        options={"verify_signature": False},
        algorithms=[settings.jwt_algorithm],
    )
    exp = payload.get("exp")
    if exp is None:
        raise ValueError("Token has no expiry")
    return datetime.fromtimestamp(exp, tz=timezone.utc)
