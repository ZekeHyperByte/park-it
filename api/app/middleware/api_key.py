"""API key authentication for internal/machine endpoints."""

import logging
import secrets

from fastapi import Header, HTTPException, status

from shared.config import get_settings

logger = logging.getLogger(__name__)


def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key")) -> bool:
    """Validate internal API key from X-API-Key header."""
    expected = get_settings().internal_api_key
    if not expected:
        logger.error("INTERNAL_API_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    if not secrets.compare_digest(expected, x_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return True
