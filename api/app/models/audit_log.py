"""Audit log model for tracking sensitive operations."""

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class AuditLog(Base, IntPKMixin, TimestampMixin):
    """Audit log entry for compliance and security monitoring.

    Tracks all sensitive operations: payments, gate operations,
    settings changes, user management, etc.
    """

    __tablename__ = "audit_logs"

    # Who performed the action
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # What action was performed
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # e.g. CASH_PAYMENT, RFID_PAYMENT, EMONEY_PAYMENT,
    #      MANUAL_GATE_OPEN, SETTING_UPDATE, USER_CREATE, etc.

    # What entity was affected
    entity_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    # e.g. ParkingTransaction, Gate, Setting, User
    entity_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Action details (flexible JSON)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Request metadata
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp (explicit for query performance)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_audit_action_time", "action", "created_at"),
        Index("idx_audit_user_time", "user_id", "created_at"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action={self.action}, "
            f"user={self.username}, entity={self.entity_type}:{self.entity_id})>"
        )
