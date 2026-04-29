"""Abandoned vehicle log model."""

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class AbandonedVehicleLog(Base, IntPKMixin, TimestampMixin):
    """Log of vehicles that timed out at exit without payment."""

    __tablename__ = "abandoned_vehicle_logs"

    gate_out_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("gates.id"), nullable=False, index=True
    )
    parking_transaction_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("parking_transactions.id"), nullable=True, index=True
    )

    # Snapshot reference
    snapshot_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("snapshots.id"), nullable=True
    )

    # Timing
    waiting_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    # Resolution
    resolution_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # VEHICLE_LEFT, MANUAL_OPEN, OPERATOR_RESET

    # Operator action
    resolved_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AbandonedVehicleLog(id={self.id}, gate={self.gate_out_id}, "
            f"resolution={self.resolution_type})>"
        )
