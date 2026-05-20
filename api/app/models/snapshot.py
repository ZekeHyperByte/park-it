"""Snapshot model for camera captures."""

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class Snapshot(Base, IntPKMixin, TimestampMixin):
    """Camera snapshot record."""

    __tablename__ = "snapshots"

    parking_transaction_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )
    gate_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    gate_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # 'in' or 'out'
    snapshot_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="entry"
    )  # entry, exit

    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # OCR / plate detection
    detected_plate: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )
    confidence: Mapped[float | None] = mapped_column(nullable=True)

    # Metadata
    camera_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Snapshot(id={self.id}, tx_id={self.parking_transaction_id}, type={self.snapshot_type})>"
