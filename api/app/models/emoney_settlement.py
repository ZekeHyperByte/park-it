"""E-money settlement model."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class EmoneySettlement(Base, IntPKMixin, TimestampMixin):
    """Settlement file tracking."""

    __tablename__ = "emoney_settlements"

    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Batch info
    batch_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    batch_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Transaction summary
    total_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status: GENERATED → UPLOADED → ACKED_OK | ACKED_NOK | PARTIAL | FAILED
    # (Pre-existing rows may carry PENDING/ACCEPTED/REJECTED.)
    status: Mapped[str] = mapped_column(
        String(20), default="GENERATED", nullable=False
    )

    # Upload tracking
    uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Bank response tracking (Multibank v1.3 §II)
    bank_response_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    bank_response_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bank_response_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    response_extension: Mapped[str | None] = mapped_column(String(4), nullable=True)
    """'OK' or 'NOK' — which response file the bank returned."""

    # Settlement file content (for audit)
    file_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    transactions: Mapped[list["EmoneyTransaction"]] = relationship(
        "EmoneyTransaction",
        lazy="selectin",
        back_populates="settlement",
    )

    def __repr__(self) -> str:
        return (
            f"<EmoneySettlement(id={self.id}, file={self.filename}, "
            f"status={self.status})>"
        )
