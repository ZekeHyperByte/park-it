"""gate sane defaults — make gate_open_timeout_s NOT NULL DEFAULT 10
and ensure hardware_config has display.enabled key.

Kills two field bugs seen during trial:
  1. gate_open_timeout_s NULL → daemon crashes on asyncio.sleep(None).
  2. hardware_config missing display.enabled → daemon sends cmd_ds and
     disconnects Compass controllers without display module.

Revision ID: a3f4b1d2e5c6
Revises: c8d9e0f1a2b3
Create Date: 2026-05-20

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3f4b1d2e5c6"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Backfill NULLs then enforce NOT NULL + default.
    op.execute("UPDATE gates SET gate_open_timeout_s = 10 WHERE gate_open_timeout_s IS NULL")
    op.alter_column(
        "gates",
        "gate_open_timeout_s",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("10"),
    )

    # 2. Ensure hardware_config has display + audio keys with safe defaults.
    #    display.enabled defaults to false (safe: no cmd_ds sent until tech
    #    confirms a display module exists). audio.enabled defaults to false.
    op.execute(
        """
        UPDATE gates
        SET hardware_config = jsonb_set(
            jsonb_set(
                COALESCE(hardware_config, '{}'::jsonb),
                '{display}',
                COALESCE(hardware_config->'display', '{"enabled": false}'::jsonb),
                true
            ),
            '{audio}',
            COALESCE(hardware_config->'audio', '{"enabled": false}'::jsonb),
            true
        )
        WHERE hardware_config IS NULL
           OR NOT (hardware_config ? 'display')
           OR NOT (hardware_config ? 'audio')
        """
    )

    # 3. Server default for hardware_config so new rows always start sane.
    op.alter_column(
        "gates",
        "hardware_config",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text(
            "'{\"display\": {\"enabled\": false}, \"audio\": {\"enabled\": false}}'::jsonb"
        ),
    )


def downgrade() -> None:
    op.alter_column(
        "gates",
        "hardware_config",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    op.alter_column(
        "gates",
        "gate_open_timeout_s",
        existing_type=sa.Integer(),
        nullable=True,
        server_default=None,
    )
