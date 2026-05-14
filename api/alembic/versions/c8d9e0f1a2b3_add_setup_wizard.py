"""add setup wizard state

Revision ID: c8d9e0f1a2b3
Revises: b2c3d4e5f6a7
Create Date: 2026-05-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "setup_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_token", sa.String(length=128), nullable=False),
        sa.Column("current_step", sa.String(length=50), nullable=False, server_default="welcome"),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_token"),
    )
    op.create_index(
        "ix_setup_sessions_session_token",
        "setup_sessions",
        ["session_token"],
        unique=True,
    )

    # Seed setup_complete=false so middleware can read it on first request.
    op.execute(
        """
        INSERT INTO settings (key, value, value_type, label, description, "group", is_system, created_at, updated_at)
        VALUES (
            'setup_complete',
            'false',
            'bool',
            'Setup wizard complete',
            'Set to true once the setup wizard finalizes. When false, middleware redirects to /setup.',
            'system',
            true,
            now(),
            now()
        )
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key = 'setup_complete'")
    op.drop_index("ix_setup_sessions_session_token", table_name="setup_sessions")
    op.drop_table("setup_sessions")
