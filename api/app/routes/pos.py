"""POS (booth) management routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin, require_auth
from api.app.models.pos import Pos
from api.app.schemas.common import SuccessResponse
from api.app.schemas.pos import PosCreate, PosResponse, PosUpdate
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("pos_routes")
router = APIRouter(prefix="/pos", tags=["POS / Booth"])


@router.get("/by-ip", response_model=PosResponse)
async def get_pos_by_ip(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_auth),
) -> PosResponse:
    """Get POS booth by client IP address.

    Used by POS frontend to auto-detect which booth this PC belongs to.
    Falls back to X-Forwarded-For if behind a proxy.
    """
    # Get client IP (handle proxy)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else None

    if not client_ip:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine client IP")

    # Try exact match first
    result = await db.execute(select(Pos).where(Pos.ip_address == client_ip))
    pos = result.scalar_one_or_none()

    # Fallback: try matching without port or handle localhost
    if pos is None and client_ip in ("127.0.0.1", "::1", "localhost"):
        # For local development, return the first active POS
        result = await db.execute(select(Pos).where(Pos.is_active == True).limit(1))
        pos = result.scalar_one_or_none()

    if pos is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No POS booth configured for IP {client_ip}",
        )

    logger.info("pos_detected_by_ip", pos_id=pos.id, code=pos.code, ip=client_ip)
    return PosResponse.model_validate(pos)


@router.get("", response_model=list[PosResponse])
async def list_pos(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[PosResponse]:
    """List all POS booths."""
    result = await db.execute(select(Pos))
    pos_list = result.scalars().all()
    return [PosResponse.model_validate(p) for p in pos_list]


@router.post("", response_model=PosResponse, status_code=status.HTTP_201_CREATED)
async def create_pos(
    data: PosCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> PosResponse:
    """Create a new POS booth."""
    pos = Pos(**data.model_dump())
    db.add(pos)
    await db.commit()
    await db.refresh(pos)
    logger.info("pos_created", pos_id=pos.id, code=pos.code)
    return PosResponse.model_validate(pos)


@router.get("/{pos_id}", response_model=PosResponse)
async def get_pos(
    pos_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> PosResponse:
    """Get POS by ID."""
    pos = await db.get(Pos, pos_id)
    if pos is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POS not found")
    return PosResponse.model_validate(pos)


@router.patch("/{pos_id}", response_model=PosResponse)
async def update_pos(
    pos_id: int,
    data: PosUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> PosResponse:
    """Update POS configuration."""
    pos = await db.get(Pos, pos_id)
    if pos is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POS not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pos, field, value)

    await db.commit()
    await db.refresh(pos)
    logger.info("pos_updated", pos_id=pos.id)
    return PosResponse.model_validate(pos)


@router.delete("/{pos_id}", response_model=SuccessResponse)
async def delete_pos(
    pos_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete POS booth."""
    pos = await db.get(Pos, pos_id)
    if pos is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POS not found")
    await db.delete(pos)
    await db.commit()
    logger.info("pos_deleted", pos_id=pos_id)
    return SuccessResponse(message="POS deleted")
