"""Parking area model."""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class AreaParkir(Base, IntPKMixin, TimestampMixin):
    """Parking area with capacity tracking."""

    __tablename__ = "area_parkir"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<AreaParkir(id={self.id}, name={self.name}, current={self.current}/{self.capacity})>"
