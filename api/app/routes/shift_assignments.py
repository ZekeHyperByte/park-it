"""Shift assignment routes (admin only)."""

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.shift_assignment import ShiftAssignment
from api.app.schemas.common import SuccessResponse
from api.app.schemas.shift_assignment import (
    ShiftAssignmentCreate,
    ShiftAssignmentResponse,
    ShiftAssignmentUpdate,
)
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("shift_assignment_routes")

router = APIRouter(prefix="/shift-assignments", tags=["Shift Assignments"])


@router.get("", response_model=list[ShiftAssignmentResponse])
async def list_shift_assignments(
    date_filter: date | None = None,
    shift_id: int | None = None,
    gate_id: int | None = None,
    worker_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[ShiftAssignmentResponse]:
    """List shift assignments with optional filters."""
    stmt = select(ShiftAssignment).order_by(ShiftAssignment.date, ShiftAssignment.shift_id)
    if date_filter is not None:
        stmt = stmt.where(ShiftAssignment.date == date_filter)
    if shift_id is not None:
        stmt = stmt.where(ShiftAssignment.shift_id == shift_id)
    if gate_id is not None:
        stmt = stmt.where(ShiftAssignment.gate_id == gate_id)
    if worker_id is not None:
        stmt = stmt.where(ShiftAssignment.worker_id == worker_id)
    result = await db.execute(stmt)
    assignments = result.scalars().all()
    return [ShiftAssignmentResponse.model_validate(a) for a in assignments]


@router.post("", response_model=ShiftAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_shift_assignment(
    data: ShiftAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> ShiftAssignmentResponse:
    """Create a shift assignment (assign worker to shift at booth on date)."""
    from fastapi import HTTPException

    # Check unique constraint before hitting DB error
    existing = await db.execute(
        select(ShiftAssignment).where(
            and_(
                ShiftAssignment.shift_id == data.shift_id,
                ShiftAssignment.gate_id == data.gate_id,
                ShiftAssignment.date == data.date,
            )
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shift already assigned for this gate on this date",
        )

    assignment = ShiftAssignment(
        **data.model_dump(),
        assigned_by=int(current_user["sub"]),
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    logger.info(
        "shift_assignment_created",
        id=assignment.id,
        shift_id=assignment.shift_id,
        gate_id=assignment.gate_id,
        date=str(assignment.date),
    )
    return ShiftAssignmentResponse.model_validate(assignment)


@router.patch("/{assignment_id}", response_model=ShiftAssignmentResponse)
async def update_shift_assignment(
    assignment_id: int,
    data: ShiftAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> ShiftAssignmentResponse:
    """Update a shift assignment (reassign worker or update notes)."""
    from fastapi import HTTPException

    assignment = await db.get(ShiftAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(assignment, field, value)

    await db.commit()
    await db.refresh(assignment)
    logger.info("shift_assignment_updated", id=assignment_id)
    return ShiftAssignmentResponse.model_validate(assignment)


@router.delete("/{assignment_id}", response_model=SuccessResponse)
async def delete_shift_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete a shift assignment."""
    from fastapi import HTTPException

    assignment = await db.get(ShiftAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await db.delete(assignment)
    await db.commit()
    logger.info("shift_assignment_deleted", id=assignment_id)
    return SuccessResponse(message="Assignment deleted")
