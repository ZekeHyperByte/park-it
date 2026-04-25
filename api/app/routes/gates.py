"""Gate management routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.gate_in import GateIn
from api.app.models.gate_out import GateOut
from api.app.schemas.common import SuccessResponse
from api.app.schemas.gate import (
    GateInCreate,
    GateInResponse,
    GateInUpdate,
    GateOutCreate,
    GateOutResponse,
    GateOutUpdate,
)
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("gate_routes")

router = APIRouter(prefix="/gates", tags=["Gates"])


# =============================================================================
# Gate In
# =============================================================================

@router.get("/in", response_model=list[GateInResponse])
async def list_gate_ins(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[GateInResponse]:
    """List all gate-in configurations."""
    result = await db.execute(select(GateIn))
    gates = result.scalars().all()
    return [GateInResponse.model_validate(g) for g in gates]


@router.post("/in", response_model=GateInResponse, status_code=status.HTTP_201_CREATED)
async def create_gate_in(
    data: GateInCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateInResponse:
    """Create a new gate-in."""
    gate = GateIn(**data.model_dump())
    db.add(gate)
    await db.commit()
    await db.refresh(gate)
    logger.info("gate_in_created", gate_id=gate.id, code=gate.code)
    return GateInResponse.model_validate(gate)


@router.get("/in/{gate_id}", response_model=GateInResponse)
async def get_gate_in(
    gate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateInResponse:
    """Get gate-in by ID."""
    from fastapi import HTTPException

    gate = await db.get(GateIn, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate in not found")
    return GateInResponse.model_validate(gate)


@router.patch("/in/{gate_id}", response_model=GateInResponse)
async def update_gate_in(
    gate_id: int,
    data: GateInUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateInResponse:
    """Update gate-in."""
    from fastapi import HTTPException

    gate = await db.get(GateIn, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate in not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(gate, field, value)

    await db.commit()
    await db.refresh(gate)
    logger.info("gate_in_updated", gate_id=gate.id)
    return GateInResponse.model_validate(gate)


@router.delete("/in/{gate_id}", response_model=SuccessResponse)
async def delete_gate_in(
    gate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete gate-in."""
    from fastapi import HTTPException

    gate = await db.get(GateIn, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate in not found")
    await db.delete(gate)
    await db.commit()
    logger.info("gate_in_deleted", gate_id=gate_id)
    return SuccessResponse(message="Gate in deleted")


# =============================================================================
# Gate Out
# =============================================================================

@router.get("/out", response_model=list[GateOutResponse])
async def list_gate_outs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[GateOutResponse]:
    """List all gate-out configurations."""
    result = await db.execute(select(GateOut))
    gates = result.scalars().all()
    return [GateOutResponse.model_validate(g) for g in gates]


@router.post("/out", response_model=GateOutResponse, status_code=status.HTTP_201_CREATED)
async def create_gate_out(
    data: GateOutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateOutResponse:
    """Create a new gate-out."""
    gate = GateOut(**data.model_dump())
    db.add(gate)
    await db.commit()
    await db.refresh(gate)
    logger.info("gate_out_created", gate_id=gate.id, code=gate.code)
    return GateOutResponse.model_validate(gate)


@router.get("/out/{gate_id}", response_model=GateOutResponse)
async def get_gate_out(
    gate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateOutResponse:
    """Get gate-out by ID."""
    from fastapi import HTTPException

    gate = await db.get(GateOut, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate out not found")
    return GateOutResponse.model_validate(gate)


@router.patch("/out/{gate_id}", response_model=GateOutResponse)
async def update_gate_out(
    gate_id: int,
    data: GateOutUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateOutResponse:
    """Update gate-out."""
    from fastapi import HTTPException

    gate = await db.get(GateOut, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate out not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(gate, field, value)

    await db.commit()
    await db.refresh(gate)
    logger.info("gate_out_updated", gate_id=gate.id)
    return GateOutResponse.model_validate(gate)


@router.delete("/out/{gate_id}", response_model=SuccessResponse)
async def delete_gate_out(
    gate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete gate-out."""
    from fastapi import HTTPException

    gate = await db.get(GateOut, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate out not found")
    await db.delete(gate)
    await db.commit()
    logger.info("gate_out_deleted", gate_id=gate_id)
    return SuccessResponse(message="Gate out deleted")
