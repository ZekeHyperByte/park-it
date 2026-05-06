"""Unified gate management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin, require_operator
from api.app.models.gate import Gate
from api.app.schemas.common import SuccessResponse
from api.app.schemas.gate import GateCreate, GateResponse, GateUpdate
from api.app.schemas.gate_control import GateControlRequest, GateControlResponse
from api.app.services.gate_command import publish_command
from api.database import get_db
from shared.events import CloseGateCommand, OpenGateCommand
from shared.logging import get_logger

logger = get_logger("gate_routes")
router = APIRouter(prefix="/gates", tags=["Gates"])


@router.get("", response_model=list[GateResponse])
async def list_gates(
    direction: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[GateResponse]:
    """List all gates, optionally filtered by direction."""
    query = select(Gate)
    if direction:
        query = query.where(Gate.direction == direction.upper())
    result = await db.execute(query)
    gates = result.scalars().all()
    return [GateResponse.model_validate(g) for g in gates]


@router.post("", response_model=GateResponse, status_code=status.HTTP_201_CREATED)
async def create_gate(
    data: GateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateResponse:
    """Create a new gate (entry or exit)."""
    gate = Gate(**data.model_dump())
    db.add(gate)
    await db.commit()
    await db.refresh(gate)
    logger.info("gate_created", gate_id=gate.id, code=gate.code, direction=gate.direction)
    return GateResponse.model_validate(gate)


@router.get("/{gate_id}", response_model=GateResponse)
async def get_gate(
    gate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateResponse:
    """Get gate by ID."""
    gate = await db.get(Gate, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    return GateResponse.model_validate(gate)


@router.patch("/{gate_id}", response_model=GateResponse)
async def update_gate(
    gate_id: int,
    data: GateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateResponse:
    """Update gate configuration."""
    gate = await db.get(Gate, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(gate, field, value)

    await db.commit()
    await db.refresh(gate)
    logger.info("gate_updated", gate_id=gate.id)
    return GateResponse.model_validate(gate)


@router.delete("/{gate_id}", response_model=SuccessResponse)
async def delete_gate(
    gate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete gate."""
    gate = await db.get(Gate, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    await db.delete(gate)
    await db.commit()
    logger.info("gate_deleted", gate_id=gate_id)
    return SuccessResponse(message="Gate deleted")


@router.post("/{gate_id}/open", response_model=GateControlResponse)
async def open_gate(
    gate_id: int,
    req: GateControlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
) -> GateControlResponse:
    """Manually open a gate. Operator triggered."""
    gate = await db.get(Gate, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    if not gate.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gate is not active")

    cmd = OpenGateCommand(gate_id=gate.code, reason=req.reason)
    msg_id = await publish_command(cmd)
    logger.info("gate_open_commanded", gate_id=gate.code, reason=req.reason)
    return GateControlResponse(success=True, message="Gate open command sent", gate_id=gate.code, command_id=msg_id)


@router.post("/{gate_id}/close", response_model=GateControlResponse)
async def close_gate(
    gate_id: int,
    req: GateControlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
) -> GateControlResponse:
    """Manually close a gate (DUAL relay mode only)."""
    gate = await db.get(Gate, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    if not gate.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gate is not active")
    if gate.relay_mode != "DUAL":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gate does not support close command (relay_mode must be DUAL)")

    cmd = CloseGateCommand(gate_id=gate.code, reason=req.reason)
    msg_id = await publish_command(cmd)
    logger.info("gate_close_commanded", gate_id=gate.code, reason=req.reason)
    return GateControlResponse(success=True, message="Gate close command sent", gate_id=gate.code, command_id=msg_id)
