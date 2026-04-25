"""Health check route."""

from fastapi import APIRouter

from shared.logging import get_logger

logger = get_logger("api.health")
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return API health status."""
    logger.debug("health_check_called")
    return {"status": "ok"}
