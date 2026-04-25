"""Shift Pydantic schemas."""

from datetime import time

from pydantic import BaseModel, ConfigDict, Field


class ShiftBase(BaseModel):
    """Base shift fields."""

    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=1, max_length=20)
    start_time: time
    end_time: time
    is_active: bool = True
    description: str | None = Field(None, max_length=255)


class ShiftCreate(ShiftBase):
    """Create shift request."""

    pass


class ShiftUpdate(BaseModel):
    """Update shift request (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=50)
    code: str | None = Field(None, min_length=1, max_length=20)
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None
    description: str | None = Field(None, max_length=255)


class ShiftResponse(ShiftBase):
    """Shift response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
