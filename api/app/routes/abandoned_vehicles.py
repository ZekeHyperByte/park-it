"""Abandoned vehicle log list routes (operator/admin)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_operator
from api.app.models.abandoned_vehicle_log import AbandonedVehicleLog
from api.app.utils.pagination import PaginatedList
from api.app.utils.pagination import PaginationParams, paginated_list
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("abandoned_vehicle_routes")

router = APIRouter(prefix="/abandoned-vehicle-logs", tags=["Abandoned Vehicle Logs"])


@router.get("", response_model=PaginatedList)
async def list_abandoned_vehicle_logs(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
) -> PaginatedList:
    """List abandoned vehicle logs."""
    stmt = select(AbandonedVehicleLog).order_by(AbandonedVehicleLog.created_at.desc())
    result = await paginated_list(db, stmt, skip=pagination.skip, limit=pagination.limit)
    return result
