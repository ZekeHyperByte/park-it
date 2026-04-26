"""Health check routes."""

from fastapi import APIRouter, Query
from redis.asyncio import Redis
from sqlalchemy import text

from api.database import get_db
from shared.config import get_settings
from shared.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger("api.health")


@router.get("/health")
async def health_check(detailed: bool = Query(default=False)) -> dict:
    """Return API health status.

    With ?detailed=true, checks database and Redis connectivity.
    """
    if not detailed:
        return {"status": "ok", "service": "parking-api"}

    checks = {
        "api": {"status": "ok"},
        "database": {"status": "unknown"},
        "redis": {"status": "unknown"},
    }
    overall = "ok"

    # Check database
    try:
        db_gen = get_db()
        db = await anext(db_gen)
        await db.execute(text("SELECT 1"))
        checks["database"]["status"] = "ok"
        await db_gen.aclose()
    except Exception as e:
        checks["database"]["status"] = "error"
        checks["database"]["error"] = str(e)
        overall = "degraded"

    # Check Redis
    try:
        settings = get_settings()
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        checks["redis"]["status"] = "ok"
        await redis.aclose()
    except Exception as e:
        checks["redis"]["status"] = "error"
        checks["redis"]["error"] = str(e)
        overall = "degraded"

    return {
        "status": overall,
        "service": "parking-api",
        "checks": checks,
    }
