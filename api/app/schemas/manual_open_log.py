"""Manual open log Pydantic schemas."""

from pydantic import BaseModel, ConfigDict


class ManualOpenLogListItem(BaseModel):
    """Manual open log list item response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    gate_id: int
    gate_type: str
    opened_by: int
    parking_transaction_id: int | None
    reason: str
    notes: str | None
    created_at: str | None = None

    @classmethod
    def model_validate(cls, obj, **kwargs):
        data = {
            "id": obj.id,
            "gate_id": obj.gate_id,
            "gate_type": obj.gate_type,
            "opened_by": obj.opened_by,
            "parking_transaction_id": obj.parking_transaction_id,
            "reason": obj.reason,
            "notes": obj.notes,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }
        return cls(**data)
