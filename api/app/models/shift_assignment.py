"""Shift assignment model — planned worker-to-shift-to-booth schedule."""

from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class ShiftAssignment(Base, IntPKMixin, TimestampMixin):
    """Planned assignment: which worker covers which shift at which booth on which date."""

    __tablename__ = "shift_assignments"

    shift_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shifts.id"), nullable=False, index=True
    )
    worker_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )
    gate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("gates.id"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    is_substitute: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_worker_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    assigned_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    shift: Mapped["Shift"] = relationship("Shift", lazy="selectin", foreign_keys=[shift_id])
    worker: Mapped["User"] = relationship("User", lazy="selectin", foreign_keys=[worker_id])
    gate: Mapped["Gate"] = relationship("Gate", lazy="selectin", foreign_keys=[gate_id])
    original_worker: Mapped["User | None"] = relationship(
        "User", lazy="selectin", foreign_keys=[original_worker_id]
    )

    __table_args__ = (
        UniqueConstraint("shift_id", "gate_id", "date", name="uq_shift_gate_date"),
    )

    def __repr__(self) -> str:
        return f"<ShiftAssignment(id={self.id}, shift_id={self.shift_id}, worker_id={self.worker_id}, date={self.date})>"
