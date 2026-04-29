"""POS (booth) model for exit gate operator stations."""

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class Pos(Base, IntPKMixin, TimestampMixin):
    """Point of Sale booth configuration."""

    __tablename__ = "pos"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Assigned gate for this booth (OUT gates only)
    default_gate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("gates.id"), nullable=True
    )

    # Booth peripherals configuration
    booth_peripherals: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    gates: Mapped[list["Gate"]] = relationship("Gate", back_populates="pos", foreign_keys="Gate.pos_id")
    default_gate: Mapped["Gate | None"] = relationship("Gate", foreign_keys=[default_gate_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<Pos(id={self.id}, name={self.name}, ip={self.ip_address})>"

    def get_peripheral(self, key: str) -> dict:
        return self.booth_peripherals.get(key, {})

    def is_peripheral_enabled(self, key: str) -> bool:
        return self.get_peripheral(key).get("enabled", False)
