"""Member model."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class Member(Base, IntPKMixin, TimestampMixin):
    """RFID member with card and vehicle info."""

    __tablename__ = "members"

    card_number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Vehicle info
    plate_number: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )
    vehicle_type_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("vehicle_types.id"), nullable=True
    )

    # Membership
    member_group_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("member_groups.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Metadata
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_entry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    vehicle_type: Mapped["VehicleType | None"] = relationship(
        "VehicleType", lazy="selectin"
    )
    member_group: Mapped["MemberGroup | None"] = relationship(
        "MemberGroup", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Member(id={self.id}, card={self.card_number}, name={self.name})>"
