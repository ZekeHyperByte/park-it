"""POS Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field


class PosBase(BaseModel):
    """Base POS fields."""

    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    ip_address: str | None = Field(None, max_length=45)
    default_gate_id: int | None = None
    booth_peripherals: dict = Field(default_factory=dict)
    is_active: bool = True


class PosCreate(PosBase):
    """Create POS request."""

    pass


class PosUpdate(BaseModel):
    """Update POS request."""

    name: str | None = Field(None, max_length=100)
    code: str | None = Field(None, max_length=20)
    ip_address: str | None = Field(None, max_length=45)
    default_gate_id: int | None = None
    booth_peripherals: dict | None = None
    is_active: bool | None = None


class PosResponse(PosBase):
    """POS response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
