"""Printer model with paper counter tracking."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class Printer(Base, IntPKMixin, TimestampMixin):
    """A thermal printer attached to a gate."""

    __tablename__ = "printers"

    # Gate reference
    gate_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    gate_type: Mapped[str] = mapped_column(
        String(10), default="IN", nullable=False
    )  # IN, OUT

    # Connection
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(
        String(30), default="CONTROLLER_PASSTHROUGH", nullable=False
    )  # CONTROLLER_PASSTHROUGH, NETWORK, SERIAL
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    serial_device: Mapped[str | None] = mapped_column(String(100), nullable=True)
    baudrate: Mapped[int] = mapped_column(Integer, default=9600, nullable=False)

    # Location (backward compat: gate_id/gate_type during transition)
    pos_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pos.id"), nullable=True
    )  # For receipt printers at booth

    # Paper counter
    paper_remaining: Mapped[int] = mapped_column(
        Integer, default=300, nullable=False
    )
    paper_capacity: Mapped[int] = mapped_column(
        Integer, default=300, nullable=False
    )
    last_refilled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Printer(id={self.id}, gate_id={self.gate_id}, paper={self.paper_remaining}/{self.paper_capacity})>"
