"""Add booth heartbeat fields to pos table.

Booth bridge POSTs /api/pos/heartbeat every 15s. The server records when
the booth last checked in (``last_seen_at``) and the most recent self-
reported status snapshot (``last_status``: rfid_connected, gate_connected,
ws_clients, last_card_at, bridge_version). Admin UI uses last_seen_at to
flag stale booths; parking-doctor surfaces them in field diagnostics.

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-05-29

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pos",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pos",
        sa.Column(
            "last_status",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    # Index supports admin UI list query ordered by staleness.
    op.create_index(
        "ix_pos_last_seen_at",
        "pos",
        ["last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pos_last_seen_at", table_name="pos")
    op.drop_column("pos", "last_status")
    op.drop_column("pos", "last_seen_at")
