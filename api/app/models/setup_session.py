"""Setup wizard session state — temporary, deleted on finalize or expiry."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class SetupSession(Base, IntPKMixin, TimestampMixin):
    """Wizard progress, keyed by setup session token.

    Created on token redeem. Updated on step transitions. Deleted on finalize.
    """

    __tablename__ = "setup_sessions"

    session_token: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    current_step: Mapped[str] = mapped_column(String(50), default="welcome", nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<SetupSession(id={self.id}, step={self.current_step})>"
