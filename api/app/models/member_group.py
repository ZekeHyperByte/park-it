"""Member group model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class MemberGroup(Base, IntPKMixin, TimestampMixin):
    """Member group for bulk pricing."""

    __tablename__ = "member_groups"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<MemberGroup(id={self.id}, name={self.name})>"
