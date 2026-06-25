"""Shift management routes (admin only)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin, require_operator
from api.app.models.shift import Shift
from api.app.schemas.common import SuccessResponse
from api.app.schemas.shift import ShiftCreate, ShiftResponse, ShiftUpdate
from api.app.utils.pagination import PaginationParams, paginated_list
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("shift_routes")

router = APIRouter(prefix="/shifts", tags=["Shifts"])


@router.get("/active", response_model=list[ShiftResponse])
async def list_active_shifts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
) -> list[ShiftResponse]:
    """List all shifts (operator-accessible, for dashboard display)."""
    stmt = select(Shift).where(Shift.is_active.is_(True)).order_by(Shift.start_time)
    result = await db.execute(stmt)
    shifts = result.scalars().all()
    return [ShiftResponse.model_validate(s) for s in shifts]


@router.get("", response_model=list[ShiftResponse])
async def list_shifts(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[ShiftResponse]:
    """List all shifts."""
    stmt = select(Shift)
    if pagination.q:
        stmt = stmt.where(
            Shift.name.ilike(f"%{pagination.q}%")
            | Shift.code.ilike(f"%{pagination.q}%")
        )
    result = await paginated_list(db, stmt, skip=pagination.skip, limit=pagination.limit)
    return [ShiftResponse.model_validate(s) for s in result.items]


@router.post("", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
async def create_shift(
    data: ShiftCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> ShiftResponse:
    """Create a new shift."""
    shift = Shift(**data.model_dump())
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    logger.info("shift_created", id=shift.id, code=shift.code)
    return ShiftResponse.model_validate(shift)


@router.get("/{shift_id}", response_model=ShiftResponse)
async def get_shift(
    shift_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> ShiftResponse:
    """Get shift by ID."""
    from fastapi import HTTPException

    shift = await db.get(Shift, shift_id)
    if shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    return ShiftResponse.model_validate(shift)


@router.patch("/{shift_id}", response_model=ShiftResponse)
async def update_shift(
    shift_id: int,
    data: ShiftUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> ShiftResponse:
    """Update shift."""
    from fastapi import HTTPException

    shift = await db.get(Shift, shift_id)
    if shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(shift, field, value)

    await db.commit()
    await db.refresh(shift)
    logger.info("shift_updated", id=shift.id)
    return ShiftResponse.model_validate(shift)


@router.delete("/{shift_id}", response_model=SuccessResponse)
async def delete_shift(
    shift_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete shift."""
    from fastapi import HTTPException

    shift = await db.get(Shift, shift_id)
    if shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    await db.delete(shift)
    await db.commit()
    logger.info("shift_deleted", id=shift_id)
    return SuccessResponse(message="Shift deleted")
