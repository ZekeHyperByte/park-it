"""Member Pydantic schemas."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class MemberBase(BaseModel):
    """Base member fields."""

    card_number: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=255)
    address: str | None = Field(None, max_length=255)
    plate_number: str | None = Field(None, max_length=20)
    vehicle_type_id: int | None = None
    is_active: bool = True
    valid_from: date | None = None
    valid_until: date | None = None
    notes: str | None = Field(None, max_length=500)


class MemberCreate(MemberBase):
    """Create member request."""

    pass


class MemberUpdate(BaseModel):
    """Update member request (all fields optional)."""

    card_number: str | None = Field(None, min_length=1, max_length=32)
    name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=255)
    address: str | None = Field(None, max_length=255)
    plate_number: str | None = Field(None, max_length=20)
    vehicle_type_id: int | None = None
    is_active: bool | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    notes: str | None = Field(None, max_length=500)


class MemberResponse(MemberBase):
    """Member response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_type_name: str | None = None
    last_entry_at: str | None = None

    @classmethod
    def model_validate(cls, obj, **kwargs):
        data = {
            **{k: getattr(obj, k) for k in MemberBase.model_fields},
            "id": obj.id,
            "vehicle_type_name": obj.vehicle_type.name if obj.vehicle_type else None,
            "last_entry_at": obj.last_entry_at.isoformat() if obj.last_entry_at else None,
        }
        return cls(**data)
