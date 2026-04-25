"""Transaction Pydantic schemas for listing."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TransactionListItem(BaseModel):
    """Transaction list item response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    barcode: str | None
    card_number: str | None
    plate_number: str | None
    vehicle_type_name: str | None
    gate_in_name: str | None
    gate_out_name: str | None
    entry_time: datetime
    exit_time: datetime | None
    payment_method: str | None
    fee: int | None
    paid_amount: int | None
    status: str
    shift_name: str | None
    operator_name: str | None
    duration_minutes: int | None = None

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Calculate duration
        duration = None
        if obj.exit_time and obj.entry_time:
            duration = int((obj.exit_time - obj.entry_time).total_seconds() / 60)

        data = {
            "id": obj.id,
            "barcode": obj.barcode,
            "card_number": obj.card_number,
            "plate_number": obj.plate_number,
            "vehicle_type_name": obj.vehicle_type.name if obj.vehicle_type else None,
            "gate_in_name": obj.gate_in.name if obj.gate_in else None,
            "gate_out_name": obj.gate_out.name if obj.gate_out else None,
            "entry_time": obj.entry_time,
            "exit_time": obj.exit_time,
            "payment_method": obj.payment_method,
            "fee": obj.fee,
            "paid_amount": obj.paid_amount,
            "status": obj.status,
            "shift_name": obj.shift.name if obj.shift else None,
            "operator_name": obj.operator.username if obj.operator else None,
            "duration_minutes": duration,
        }
        return cls(**data)
