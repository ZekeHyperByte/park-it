"""Manual open log model."""

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class ManualOpenLog(Base, IntPKMixin, TimestampMixin):
    """Log of manual gate opens by operator."""

    __tablename__ = "manual_open_logs"

    gate_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    gate_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # 'in' or 'out'
    opened_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    parking_transaction_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("parking_transactions.id"), nullable=True
    )

    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ManualOpenLog(id={self.id}, gate_id={self.gate_id}, reason={self.reason})>"
