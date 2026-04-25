"""Member renewal model."""

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class MemberRenewal(Base, IntPKMixin, TimestampMixin):
    """Member renewal / payment history."""

    __tablename__ = "member_renewals"

    member_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("members.id"), nullable=False, index=True
    )
    renewed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )

    # Renewal details
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    amount_paid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(20), default="CASH", nullable=False
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    member: Mapped["Member"] = relationship("Member", lazy="selectin")

    def __repr__(self) -> str:
        return f"<MemberRenewal(id={self.id}, member_id={self.member_id}, until={self.valid_until})>"
