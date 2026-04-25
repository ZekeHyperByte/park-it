"""Health check model."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class HealthCheck(Base, IntPKMixin, TimestampMixin):
    """System health check record."""

    __tablename__ = "health_checks"

    component: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # api, postgres, redis, gate_in_N, gate_out_N, printer_N, etc.

    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # OK, DEGRADED, DOWN

    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<HealthCheck(id={self.id}, component={self.component}, "
            f"status={self.status}, latency={self.latency_ms}ms)>"
        )
