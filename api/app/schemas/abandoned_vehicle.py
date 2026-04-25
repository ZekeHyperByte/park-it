"""Abandoned vehicle log Pydantic schemas."""

from pydantic import BaseModel, ConfigDict


class AbandonedVehicleLogListItem(BaseModel):
    """Abandoned vehicle log list item response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    gate_out_id: int
    parking_transaction_id: int | None
    snapshot_id: int | None
    waiting_seconds: int
    resolution_type: str
    resolved_by: int | None
    notes: str | None
    created_at: str | None = None

    @classmethod
    def model_validate(cls, obj, **kwargs):
        data = {
            "id": obj.id,
            "gate_out_id": obj.gate_out_id,
            "parking_transaction_id": obj.parking_transaction_id,
            "snapshot_id": obj.snapshot_id,
            "waiting_seconds": obj.waiting_seconds,
            "resolution_type": obj.resolution_type,
            "resolved_by": obj.resolved_by,
            "notes": obj.notes,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }
        return cls(**data)
