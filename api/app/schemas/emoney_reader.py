"""Emoney reader Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field


class EmoneyReaderBase(BaseModel):
    """Base emoney reader fields."""

    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    connection_type: str = Field(default="CONTROLLER_PASSTHROUGH", max_length=30)
    serial_port: str = Field(..., min_length=1, max_length=50)
    baudrate: int = Field(default=38400, ge=0)
    mid: str | None = Field(None, max_length=20)
    tid: str | None = Field(None, max_length=20)
    encrypted_init_key: str | None = Field(None, max_length=255)
    is_active: bool = True


class EmoneyReaderCreate(EmoneyReaderBase):
    """Create emoney reader request."""

    pass


class EmoneyReaderUpdate(BaseModel):
    """Update emoney reader request (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    code: str | None = Field(None, min_length=1, max_length=20)
    connection_type: str | None = Field(None, max_length=30)
    serial_port: str | None = Field(None, min_length=1, max_length=50)
    baudrate: int | None = Field(None, ge=0)
    mid: str | None = Field(None, max_length=20)
    tid: str | None = Field(None, max_length=20)
    encrypted_init_key: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class EmoneyReaderResponse(EmoneyReaderBase):
    """Emoney reader response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_online: bool
    last_heartbeat: str | None
    firmware_version: str | None
