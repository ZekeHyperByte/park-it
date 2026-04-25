"""Manual open log list routes (operator/admin)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_operator
from api.app.models.manual_open_log import ManualOpenLog
from api.app.utils.pagination import PaginatedList
from api.app.utils.pagination import PaginationParams, paginated_list
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("manual_open_log_routes")

router = APIRouter(prefix="/manual-open-logs", tags=["Manual Open Logs"])


@router.get("", response_model=PaginatedList)
async def list_manual_open_logs(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
) -> PaginatedList:
    """List manual open logs."""
    stmt = select(ManualOpenLog).order_by(ManualOpenLog.created_at.desc())
    result = await paginated_list(db, stmt, skip=pagination.skip, limit=pagination.limit)
    return result
