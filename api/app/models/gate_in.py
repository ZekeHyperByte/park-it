"""Gate-in model."""

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class GateIn(Base, IntPKMixin, TimestampMixin):
    """Entry gate configuration."""

    __tablename__ = "gate_ins"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    area_parkir_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("area_parkir.id"), nullable=True
    )

    # Protocol / hardware
    protocol: Mapped[str] = mapped_column(
        String(20), default="compass", nullable=False
    )  # compass, enet
    controller_host: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    controller_port: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Gate mode (v2 addition)
    gate_mode: Mapped[str] = mapped_column(
        String(20), default="CASH", nullable=False
    )  # CASH, RFID, EMONEY

    # E-money settings (v2 addition)
    emoney_minimum_balance: Mapped[int] = mapped_column(
        Integer, default=10000, nullable=False
    )
    print_decision_timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )

    # Hardware settings (v2 addition)
    has_close_sensor: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    gate_close_duration_ms: Mapped[int] = mapped_column(
        Integer, default=5000, nullable=False
    )
    relay_mode: Mapped[str] = mapped_column(
        String(20), default="SINGLE", nullable=False
    )  # SINGLE, DUAL

    # Gate control
    open_command: Mapped[str | None] = mapped_column(String(50), nullable=True)
    close_command: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pulse_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gate_open_timeout_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sensor_stuck_s: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Audio/LED
    audio_module: Mapped[str | None] = mapped_column(String(50), nullable=True)
    led_display: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Printer
    printer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    printer_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # escpos, etc.

    # Camera
    camera_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    camera_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_heartbeat: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    area_parkir: Mapped["AreaParkir | None"] = relationship(
        "AreaParkir", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<GateIn(id={self.id}, name={self.name}, mode={self.gate_mode})>"
