"""Add shift_assignments, worker_sessions tables and worker_pin to users.

Revision ID: b3c4d5e6f7a8
Revises: a3f4b1d2e5c6
Create Date: 2026-05-23

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a3f4b1d2e5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # worker_pin on users
    op.add_column("users", sa.Column("worker_pin", sa.String(255), nullable=True))

    # shift_assignments — planned schedule
    op.create_table(
        "shift_assignments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("shift_id", sa.BigInteger(), nullable=False),
        sa.Column("worker_id", sa.BigInteger(), nullable=False),
        sa.Column("gate_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_substitute", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("original_worker_id", sa.BigInteger(), nullable=True),
        sa.Column("assigned_by", sa.BigInteger(), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
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
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["gate_id"], ["gates.id"]),
        sa.ForeignKeyConstraint(["original_worker_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shift_id", "gate_id", "date", name="uq_shift_gate_date"),
    )
    op.create_index("ix_shift_assignments_shift_id", "shift_assignments", ["shift_id"])
    op.create_index("ix_shift_assignments_worker_id", "shift_assignments", ["worker_id"])
    op.create_index("ix_shift_assignments_gate_id", "shift_assignments", ["gate_id"])
    op.create_index("ix_shift_assignments_date", "shift_assignments", ["date"])

    # worker_sessions — operational truth
    op.create_table(
        "worker_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("shift_id", sa.BigInteger(), nullable=False),
        sa.Column("shift_assignment_id", sa.BigInteger(), nullable=True),
        sa.Column("worker_id", sa.BigInteger(), nullable=False),
        sa.Column("gate_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outgoing_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_type", sa.String(20), nullable=True),
        sa.Column("end_reason", sa.String(255), nullable=True),
        sa.Column("is_substitute", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("previous_session_id", sa.BigInteger(), nullable=True),
        sa.Column("force_leave_approved_by", sa.BigInteger(), nullable=True),
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
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"]),
        sa.ForeignKeyConstraint(["shift_assignment_id"], ["shift_assignments.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["gate_id"], ["gates.id"]),
        sa.ForeignKeyConstraint(["force_leave_approved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_sessions_shift_id", "worker_sessions", ["shift_id"])
    op.create_index("ix_worker_sessions_worker_id", "worker_sessions", ["worker_id"])
    op.create_index("ix_worker_sessions_gate_id", "worker_sessions", ["gate_id"])
    op.create_index("ix_worker_sessions_date", "worker_sessions", ["date"])
    op.create_index("ix_worker_sessions_status", "worker_sessions", ["status"])
    op.create_index(
        "ix_worker_sessions_gate_date_status",
        "worker_sessions",
        ["gate_id", "date", "status"],
    )
    op.create_index(
        "ix_worker_sessions_worker_date",
        "worker_sessions",
        ["worker_id", "date"],
    )


def downgrade() -> None:
    op.drop_table("worker_sessions")
    op.drop_table("shift_assignments")
    op.drop_column("users", "worker_pin")
