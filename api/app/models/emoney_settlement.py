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

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False
    )  # PENDING, UPLOADED, ACCEPTED, REJECTED

    # Bank response
    bank_response_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    bank_response_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bank_response_message: Mapped[str | None] = mapped_column(Text, nullable=True)

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
