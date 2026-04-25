"""E-money transaction model."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class EmoneyTransaction(Base, IntPKMixin, TimestampMixin):
    """PASSTI e-money deduct record."""

    __tablename__ = "emoney_transactions"

    # Link to parking transaction
    parking_transaction_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("parking_transactions.id"), nullable=True, index=True
    )

    # Card info
    card_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    card_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Deduct details
    amount_deducted: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    balance_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transaction_counter: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="PENDING", nullable=False, index=True
    )
    # SUCCESS, LOST_CONTACT, CORRECTION_VERIFIED, CORRECTION_FAILED,
    # TIMEOUT, FAILED, PENDING

    # Raw response
    raw_response_hex: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Settlement link
    settlement_batch_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("emoney_settlements.id"), nullable=True, index=True
    )

    # Correction tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    correction_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    parking_transaction: Mapped["ParkingTransaction | None"] = relationship(
        "ParkingTransaction",
        lazy="selectin",
        foreign_keys=[parking_transaction_id],
    )
    settlement: Mapped["EmoneySettlement | None"] = relationship(
        "EmoneySettlement", lazy="selectin", back_populates="transactions"
    )

    # Partial indexes for fast queries
    __table_args__ = (
        # Fast settlement query
        Index(
            "idx_unsettled_emoney",
            "created_at",
            postgresql_where=(
                (settlement_batch_id.is_(None)) & (status == "SUCCESS")
            ),
        ),
        # Fast correction query
        Index(
            "idx_pending_correction",
            "created_at",
            postgresql_where=(status.in_(["LOST_CONTACT", "CORRECTION_FAILED"])),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<EmoneyTransaction(id={self.id}, card={self.card_number}, "
            f"amount={self.amount_deducted}, status={self.status})>"
        )
