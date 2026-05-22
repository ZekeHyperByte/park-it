"""Shift assignment Pydantic schemas."""

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field


class ShiftAssignmentCreate(BaseModel):
    """Create shift assignment request."""

    shift_id: int
    worker_id: int
    gate_id: int
    date: date
    is_substitute: bool = False
    original_worker_id: int | None = None
    notes: str | None = Field(None, max_length=255)


class ShiftAssignmentUpdate(BaseModel):
    """Update shift assignment (reassign or add notes)."""

    worker_id: int | None = None
    is_substitute: bool | None = None
    original_worker_id: int | None = None
    notes: str | None = Field(None, max_length=255)


class ShiftSummary(BaseModel):
    """Minimal shift info embedded in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    start_time: time
    end_time: time


class WorkerSummary(BaseModel):
    """Minimal user info embedded in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str | None
    role: str


class GateSummary(BaseModel):
    """Minimal gate info embedded in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    direction: str


class ShiftAssignmentResponse(BaseModel):
    """Shift assignment response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    shift_id: int
    worker_id: int
    gate_id: int
    date: date
    is_substitute: bool
    original_worker_id: int | None
    assigned_by: int | None
    notes: str | None
    created_at: datetime

    shift: ShiftSummary | None = None
    worker: WorkerSummary | None = None
    gate: GateSummary | None = None
    original_worker: WorkerSummary | None = None
