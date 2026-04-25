"""Vehicle type model."""

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class VehicleType(Base, IntPKMixin, TimestampMixin):
    """Vehicle type with tariff configuration."""

    __tablename__ = "vehicle_types"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)

    # Tariff settings
    base_tariff: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # in IDR
    hourly_rate: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # per hour after first
    max_daily_cap: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # max per day
    lost_ticket_penalty: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Overnight mode
    overnight_mode: Mapped[str] = mapped_column(
        String(20),
        default="midnight",
        nullable=False,
    )  # midnight, 24h, none
    overnight_tariff: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Progressive pricing flag
    is_progressive: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )

    def __repr__(self) -> str:
        return f"<VehicleType(id={self.id}, name={self.name}, code={self.code})>"
