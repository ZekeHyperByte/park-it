"""Site configuration model — singleton for parking location details."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class SiteConfig(Base, IntPKMixin, TimestampMixin):
    """Singleton site configuration.

    Only one row should exist in this table. Used for receipts,
    reports, and ticket headers.
    """

    __tablename__ = "site_config"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<SiteConfig(name={self.name}, city={self.city})>"
