"""Vehicle type management routes (admin only)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.cache.reference_data import (
    get_cached_vehicle_types,
    invalidate_vehicle_types,
)
from api.app.middleware.auth import require_admin, require_auth
from api.app.models.vehicle_type import VehicleType
from api.app.schemas.common import SuccessResponse
from api.app.schemas.vehicle_type import (
    VehicleTypeCreate,
    VehicleTypeResponse,
    VehicleTypeUpdate,
)
from api.app.utils.pagination import PaginationParams, paginated_list
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("vehicle_type_routes")

router = APIRouter(prefix="/vehicle-types", tags=["Vehicle Types"])


@router.get("", response_model=list[VehicleTypeResponse])
async def list_vehicle_types(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_auth),
) -> list[VehicleTypeResponse]:
    """List all vehicle types (cached)."""
    # Only cache unfiltered, unpaginated lists
    if pagination.skip == 0 and pagination.limit == 100 and not pagination.q:
        try:
            cached = await get_cached_vehicle_types()
            if cached is not None:
                return [VehicleTypeResponse(**v) for v in cached]
        except Exception:
            pass  # Redis unavailable, fall through to DB

    stmt = select(VehicleType)
    if pagination.q:
        stmt = stmt.where(
            VehicleType.name.ilike(f"%{pagination.q}%")
            | VehicleType.code.ilike(f"%{pagination.q}%")
        )
    result = await paginated_list(db, stmt, skip=pagination.skip, limit=pagination.limit)
    items = [VehicleTypeResponse.model_validate(v) for v in result.items]

    # Cache the full unfiltered list
    if pagination.skip == 0 and pagination.limit == 100 and not pagination.q:
        try:
            from api.app.cache.reference_data import _set_cached, CACHE_KEYS
            await _set_cached(CACHE_KEYS["vehicle_types"], [v.model_dump() for v in items])
        except Exception:
            pass  # Redis unavailable, ignore

    return items


@router.post("", response_model=VehicleTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle_type(
    data: VehicleTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> VehicleTypeResponse:
    """Create a new vehicle type."""
    vt = VehicleType(**data.model_dump())
    db.add(vt)
    await db.commit()
    await db.refresh(vt)
    try:
        await invalidate_vehicle_types()
    except Exception:
        pass
    logger.info("vehicle_type_created", id=vt.id, code=vt.code)
    return VehicleTypeResponse.model_validate(vt)


@router.get("/{vt_id}", response_model=VehicleTypeResponse)
async def get_vehicle_type(
    vt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> VehicleTypeResponse:
    """Get vehicle type by ID."""
    from fastapi import HTTPException

    vt = await db.get(VehicleType, vt_id)
    if vt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle type not found")
    return VehicleTypeResponse.model_validate(vt)


@router.patch("/{vt_id}", response_model=VehicleTypeResponse)
async def update_vehicle_type(
    vt_id: int,
    data: VehicleTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> VehicleTypeResponse:
    """Update vehicle type."""
    from fastapi import HTTPException

    vt = await db.get(VehicleType, vt_id)
    if vt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle type not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(vt, field, value)

    await db.commit()
    await db.refresh(vt)
    try:
        await invalidate_vehicle_types()
    except Exception:
        pass
    logger.info("vehicle_type_updated", id=vt.id)
    return VehicleTypeResponse.model_validate(vt)


@router.delete("/{vt_id}", response_model=SuccessResponse)
async def delete_vehicle_type(
    vt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete vehicle type."""
    from fastapi import HTTPException

    vt = await db.get(VehicleType, vt_id)
    if vt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle type not found")
    await db.delete(vt)
    await db.commit()
    try:
        await invalidate_vehicle_types()
    except Exception:
        pass
    logger.info("vehicle_type_deleted", id=vt_id)
    return SuccessResponse(message="Vehicle type deleted")
