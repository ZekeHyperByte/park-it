"""Camera Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field


class CameraBase(BaseModel):
    """Base camera fields."""

    name: str = Field(..., max_length=100)
    rtsp_url: str | None = Field(None, max_length=500)
    snapshot_url: str | None = Field(None, max_length=500)
    username: str | None = Field(None, max_length=100)
    password: str | None = Field(None, max_length=255)
    type: str = Field(default="rtsp", max_length=20)
    is_active: bool = True


class CameraCreate(CameraBase):
    """Create camera request."""

    pass


class CameraUpdate(BaseModel):
    """Update camera request."""

    name: str | None = Field(None, max_length=100)
    rtsp_url: str | None = Field(None, max_length=500)
    snapshot_url: str | None = Field(None, max_length=500)
    username: str | None = Field(None, max_length=100)
    password: str | None = Field(None, max_length=255)
    type: str | None = Field(None, max_length=20)
    is_active: bool | None = None


class CameraResponse(CameraBase):
    """Camera response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
