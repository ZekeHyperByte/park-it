"""E-money reader configuration model."""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class EmoneyReader(Base, IntPKMixin, TimestampMixin):
    """PASSTI e-money reader configuration."""

    __tablename__ = "emoney_readers"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # Serial configuration
    serial_port: Mapped[str] = mapped_column(String(50), nullable=False)
    baudrate: Mapped[int] = mapped_column(Integer, default=115200, nullable=False)

    # PASSTI credentials
    mid: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # Merchant ID
    tid: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # Terminal ID
    encrypted_init_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_online: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_heartbeat: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Firmware / version
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<EmoneyReader(id={self.id}, name={self.name}, port={self.serial_port})>"
