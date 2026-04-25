"""Area parkir management routes (admin only)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.area_parkir import AreaParkir
from api.app.schemas.area import AreaCreate, AreaResponse, AreaUpdate
from api.app.schemas.common import SuccessResponse
from api.app.utils.pagination import PaginationParams, paginated_list
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("area_routes")

router = APIRouter(prefix="/areas", tags=["Areas"])


@router.get("", response_model=list[AreaResponse])
async def list_areas(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[AreaResponse]:
    """List all parking areas."""
    stmt = select(AreaParkir)
    if pagination.q:
        stmt = stmt.where(
            AreaParkir.name.ilike(f"%{pagination.q}%")
            | AreaParkir.code.ilike(f"%{pagination.q}%")
        )
    result = await paginated_list(db, stmt, skip=pagination.skip, limit=pagination.limit)
    return [AreaResponse.model_validate(a) for a in result.items]


@router.post("", response_model=AreaResponse, status_code=status.HTTP_201_CREATED)
async def create_area(
    data: AreaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> AreaResponse:
    """Create a new parking area."""
    area = AreaParkir(**data.model_dump())
    db.add(area)
    await db.commit()
    await db.refresh(area)
    logger.info("area_created", id=area.id, code=area.code)
    return AreaResponse.model_validate(area)


@router.get("/{area_id}", response_model=AreaResponse)
async def get_area(
    area_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> AreaResponse:
    """Get area by ID."""
    from fastapi import HTTPException

    area = await db.get(AreaParkir, area_id)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return AreaResponse.model_validate(area)


@router.patch("/{area_id}", response_model=AreaResponse)
async def update_area(
    area_id: int,
    data: AreaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> AreaResponse:
    """Update area."""
    from fastapi import HTTPException

    area = await db.get(AreaParkir, area_id)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(area, field, value)

    await db.commit()
    await db.refresh(area)
    logger.info("area_updated", id=area.id)
    return AreaResponse.model_validate(area)


@router.delete("/{area_id}", response_model=SuccessResponse)
async def delete_area(
    area_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete area."""
    from fastapi import HTTPException

    area = await db.get(AreaParkir, area_id)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    await db.delete(area)
    await db.commit()
    logger.info("area_deleted", id=area_id)
    return SuccessResponse(message="Area deleted")
