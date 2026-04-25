"""Member group Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field


class MemberGroupBase(BaseModel):
    """Base member group fields."""

    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    description: str | None = Field(None, max_length=255)
    is_active: bool = True


class MemberGroupCreate(MemberGroupBase):
    """Create member group request."""

    pass


class MemberGroupUpdate(BaseModel):
    """Update member group request (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    code: str | None = Field(None, min_length=1, max_length=20)
    description: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class MemberGroupResponse(MemberGroupBase):
    """Member group response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
