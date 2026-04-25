"""Shift e-money snapshot model."""

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class ShiftEmoneySnapshot(Base, IntPKMixin, TimestampMixin):
    """Per-shift, per-card-type e-money aggregation."""

    __tablename__ = "shift_emoney_snapshots"

    shift_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shifts.id"), nullable=False, index=True
    )
    snapshot_date: Mapped[str] = mapped_column(
        Date, nullable=False, index=True
    )  # YYYY-MM-DD

    # Card type aggregation
    card_type: Mapped[str] = mapped_column(String(50), nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status breakdown
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lost_contact_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ShiftEmoneySnapshot(shift={self.shift_id}, "
            f"date={self.snapshot_date}, type={self.card_type}, "
            f"count={self.transaction_count}, amount={self.total_amount})>"
        )
