"""Camera entity for RTSP surveillance."""

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class Camera(Base, IntPKMixin, TimestampMixin):
    """RTSP camera configuration."""

    __tablename__ = "cameras"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rtsp_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    snapshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[str | None] = mapped_column(String(20), default="rtsp", nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Camera(id={self.id}, name={self.name})>"
