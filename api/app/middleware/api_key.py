"""API key authentication for internal/machine endpoints."""

import os

from fastapi import Header, HTTPException, status


def _get_api_key() -> str:
    return os.environ.get("INTERNAL_API_KEY", "")


def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key")) -> str:
    """Validate internal API key from X-API-Key header."""
    expected = _get_api_key()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="INTERNAL_API_KEY not configured",
        )
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return x_api_key
