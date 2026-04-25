"""Setting Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field


class SettingBase(BaseModel):
    """Base setting fields."""

    key: str = Field(..., max_length=100)
    value: str | None = None
    value_type: str = Field(default="string", pattern="^(string|int|bool|json)$")
    label: str | None = Field(None, max_length=200)
    description: str | None = None
    group: str | None = Field(None, max_length=50)
    is_system: bool = False


class SettingCreate(SettingBase):
    """Create setting request."""

    pass


class SettingUpdate(BaseModel):
    """Update setting request."""

    value: str | None = None
    value_type: str | None = Field(None, pattern="^(string|int|bool|json)$")
    label: str | None = Field(None, max_length=200)
    description: str | None = None
    group: str | None = Field(None, max_length=50)


class SettingResponse(SettingBase):
    """Setting response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
