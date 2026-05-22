"""Worker session model — actual worked periods per booth."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class WorkerSession(Base, IntPKMixin, TimestampMixin):
    """Actual session: who worked at which booth, when.

    Differs from ShiftAssignment (planned) — this is operational truth.
    Gaps between consecutive sessions on same gate+date = uncovered periods.
    """

    __tablename__ = "worker_sessions"

    shift_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shifts.id"), nullable=False, index=True
    )
    # Nullable: substitutions may not have a pre-created assignment
    shift_assignment_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("shift_assignments.id"), nullable=True
    )
    worker_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )
    gate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("gates.id"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # State: ACTIVE | PENDING_HANDOVER | COMPLETED
    status: Mapped[str] = mapped_column(
        String(20), default="ACTIVE", nullable=False, index=True
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Option B step 1: outgoing pressed "I'm leaving"
    outgoing_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # SCHEDULED | EARLY | FORCE_LEAVE
    end_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_substitute: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # No FK constraint — avoid circular; link to previous session in same handover chain
    previous_session_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    force_leave_approved_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )

    # Relationships
    shift: Mapped["Shift"] = relationship("Shift", lazy="selectin")
    shift_assignment: Mapped["ShiftAssignment | None"] = relationship(
        "ShiftAssignment", lazy="selectin"
    )
    worker: Mapped["User"] = relationship(
        "User", lazy="selectin", foreign_keys=[worker_id]
    )
    gate: Mapped["Gate"] = relationship("Gate", lazy="selectin")

    __table_args__ = (
        Index("ix_worker_sessions_gate_date_status", "gate_id", "date", "status"),
        Index("ix_worker_sessions_worker_date", "worker_id", "date"),
    )

    def __repr__(self) -> str:
        return (
            f"<WorkerSession(id={self.id}, worker_id={self.worker_id}, "
            f"gate_id={self.gate_id}, date={self.date}, status={self.status})>"
        )
