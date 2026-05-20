"""System setting model."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class Setting(Base, IntPKMixin, TimestampMixin):
    """System-wide settings."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(
        String(20), default="string", nullable=False
    )  # string, int, bool, json

    # Description
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    group: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # general, emoney, gate, settlement, etc.

    # V2 e-money defaults (stored as settings for flexibility)
    # These are convenience columns for frequently accessed defaults:
    # - emoney_minimum_balance_default
    # - payment_timeout_seconds_default
    # - settlement_schedule
    # - settlement_auto_upload
    # They are also available as individual settings rows.

    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # protected from user deletion

    def __repr__(self) -> str:
        return f"<Setting(id={self.id}, key={self.key}, group={self.group})>"
