"""Area parkir Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field


class AreaBase(BaseModel):
    """Base area fields."""

    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    capacity: int = Field(default=0, ge=0)
    current: int = Field(default=0, ge=0)
    description: str | None = Field(None, max_length=255)


class AreaCreate(AreaBase):
    """Create area request."""

    pass


class AreaUpdate(BaseModel):
    """Update area request (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    code: str | None = Field(None, min_length=1, max_length=20)
    capacity: int | None = Field(None, ge=0)
    current: int | None = Field(None, ge=0)
    description: str | None = Field(None, max_length=255)


class AreaResponse(AreaBase):
    """Area response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
