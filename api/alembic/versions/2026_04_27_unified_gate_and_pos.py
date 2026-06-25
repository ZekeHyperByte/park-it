"""Unified Gate and Pos (booth) architecture.

Revision ID: 2026_04_27_unified_gate_and_pos
Revises: e6f9a2b3c4d5
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_04_27_unified_gate_and_pos"
down_revision: str | None = "e6f9a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create Camera table ─────────────────────────────────────────
    op.create_table(
        "cameras",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("rtsp_url", sa.String(500), nullable=True),
        sa.Column("snapshot_url", sa.String(500), nullable=True),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("password", sa.String(255), nullable=True),
        sa.Column("type", sa.String(20), nullable=True, server_default="rtsp"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
    )

    # ── 2. Create Pos (booth) table ────────────────────────────────────
    op.create_table(
        "pos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
    )

    # ── 3. Create unified Gate table ───────────────────────────────────
    op.create_table(
        "gates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("direction", sa.String(10), nullable=False),  # 'IN' or 'OUT'
        sa.Column(
            "area_parkir_id", sa.BigInteger(), sa.ForeignKey("area_parkir.id"), nullable=True
        ),
        sa.Column(
            "pos_id", sa.BigInteger(), sa.ForeignKey("pos.id"), nullable=True
        ),  # OUT gates only
        # Controller connection
        sa.Column(
            "protocol", sa.String(20), nullable=False, server_default="compass"
        ),
        sa.Column("controller_host", sa.String(100), nullable=True),
        sa.Column("controller_port", sa.Integer(), nullable=True),
        sa.Column(
            "controller_device", sa.String(100), nullable=True
        ),  # for serial protocol
        sa.Column(
            "controller_baudrate", sa.Integer(), nullable=True
        ),  # for serial protocol
        # Hardware settings
        sa.Column(
            "has_close_sensor", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "gate_close_duration_ms",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5000"),
        ),
        sa.Column(
            "relay_mode", sa.String(20), nullable=False, server_default="SINGLE"
        ),
        sa.Column("gate_open_timeout_s", sa.Integer(), nullable=True),
        sa.Column("sensor_stuck_s", sa.Integer(), nullable=True),
        # Peripherals config (JSONB)
        sa.Column(
            "hardware_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_heartbeat", sa.String(50), nullable=True),
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
        sa.CheckConstraint("direction IN ('IN', 'OUT')", name="ck_gate_direction"),
    )
    op.create_index("ix_gates_direction", "gates", ["direction"])
    op.create_index("ix_gates_pos_id", "gates", ["pos_id"])

    # ── 4. Migrate data from GateIn ────────────────────────────────────
    op.execute("""
        INSERT INTO gates (
            name, code, direction, area_parkir_id,
            protocol, controller_host, controller_port,
            has_close_sensor, gate_close_duration_ms, relay_mode,
            gate_open_timeout_s, sensor_stuck_s,
            hardware_config, is_active, is_online, last_heartbeat,
            created_at, updated_at
        )
        SELECT
            name, code, 'IN', area_parkir_id,
            protocol, controller_host, controller_port,
            has_close_sensor, gate_close_duration_ms, relay_mode,
            gate_open_timeout_s, sensor_stuck_s,
            jsonb_build_object(
                'gate_mode', gate_mode,
                'emoney_minimum_balance', emoney_minimum_balance,
                'print_decision_timeout_seconds', print_decision_timeout_seconds,
                'open_command', open_command,
                'close_command', close_command,
                'pulse_duration_ms', pulse_duration_ms,
                'ticket_printer', CASE WHEN printer_name IS NOT NULL THEN
                    jsonb_build_object(
                        'enabled', true,
                        'printer_name', printer_name,
                        'printer_type', printer_type,
                        'printer_ip_address', printer_ip_address,
                        'printer_device', printer_device
                    )
                ELSE '{}'::jsonb END,
                'camera', CASE WHEN camera_url IS NOT NULL THEN
                    jsonb_build_object(
                        'enabled', true,
                        'camera_url', camera_url,
                        'camera_name', camera_name
                    )
                ELSE '{}'::jsonb END,
                'audio', CASE WHEN audio_module IS NOT NULL THEN
                    jsonb_build_object('enabled', true, 'module', audio_module)
                ELSE '{}'::jsonb END,
                'led', CASE WHEN led_display IS NOT NULL THEN
                    jsonb_build_object('enabled', true, 'module', led_display)
                ELSE '{}'::jsonb END
            ),
            is_active, is_online, last_heartbeat,
            created_at, updated_at
        FROM gate_ins
    """)

    # ── 5. Migrate data from GateOut ───────────────────────────────────
    # First create Pos records for existing GateOuts
    op.execute("""
        INSERT INTO pos (name, code, ip_address, is_active, created_at, updated_at)
        SELECT
            name || ' Booth', code || '_POS', NULL, is_active, created_at, updated_at
        FROM gate_outs
    """)

    op.execute("""
        INSERT INTO gates (
            name, code, direction, area_parkir_id, pos_id,
            protocol, controller_host, controller_port,
            has_close_sensor, gate_close_duration_ms, relay_mode,
            gate_open_timeout_s, sensor_stuck_s,
            hardware_config, is_active, is_online, last_heartbeat,
            created_at, updated_at
        )
        SELECT
            g.name, g.code, 'OUT', g.area_parkir_id, p.id,
            g.protocol, g.controller_host, g.controller_port,
            g.has_close_sensor, g.gate_close_duration_ms, g.relay_mode,
            g.gate_open_timeout_s, g.sensor_stuck_s,
            jsonb_build_object(
                'payment_timeout_seconds', g.payment_timeout_seconds,
                'open_command', g.open_command,
                'close_command', g.close_command,
                'pulse_duration_ms', g.pulse_duration_ms,
                'emoney_reader_id', g.emoney_reader_id,
                'receipt_printer', CASE WHEN g.printer_name IS NOT NULL THEN
                    jsonb_build_object(
                        'enabled', true,
                        'printer_name', g.printer_name,
                        'printer_type', g.printer_type,
                        'printer_ip_address', g.printer_ip_address,
                        'printer_device', g.printer_device
                    )
                ELSE '{}'::jsonb END,
                'camera', CASE WHEN g.camera_url IS NOT NULL THEN
                    jsonb_build_object(
                        'enabled', true,
                        'camera_url', g.camera_url,
                        'camera_name', g.camera_name
                    )
                ELSE '{}'::jsonb END,
                'audio', CASE WHEN g.audio_module IS NOT NULL THEN
                    jsonb_build_object('enabled', true, 'module', g.audio_module)
                ELSE '{}'::jsonb END,
                'led', CASE WHEN g.led_display IS NOT NULL THEN
                    jsonb_build_object('enabled', true, 'module', g.led_display)
                ELSE '{}'::jsonb END
            ),
            g.is_active, g.is_online, g.last_heartbeat,
            g.created_at, g.updated_at
        FROM gate_outs g
        JOIN pos p ON p.code = g.code || '_POS'
    """)

    # ── 6. Create/update Printer table ─────────────────────────────────
    # NOTE: printers table may not exist in some environments;
    # create it if missing, then add pos_id.
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "printers" not in inspector.get_table_names():
        op.create_table(
            "printers",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("gate_id", sa.String(50), nullable=False, index=True),
            sa.Column("gate_type", sa.String(10), server_default="IN", nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("mode", sa.String(30), server_default="CONTROLLER_PASSTHROUGH", nullable=False),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("port", sa.Integer(), nullable=True),
            sa.Column("serial_device", sa.String(100), nullable=True),
            sa.Column("baudrate", sa.Integer(), server_default="9600", nullable=False),
            sa.Column("paper_remaining", sa.Integer(), server_default="300", nullable=False),
            sa.Column("paper_capacity", sa.Integer(), server_default="300", nullable=False),
            sa.Column("last_refilled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("pos_id", sa.BigInteger(), sa.ForeignKey("pos.id"), nullable=True),
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
        )
    else:
        op.add_column(
            "printers", sa.Column("pos_id", sa.BigInteger(), sa.ForeignKey("pos.id"), nullable=True)
        )
    op.create_index("ix_printers_pos_id", "printers", ["pos_id"])

    # ── 7. Update ParkingTransaction foreign keys ──────────────────────
    op.add_column(
        "parking_transactions",
        sa.Column("gate_id", sa.BigInteger(), sa.ForeignKey("gates.id"), nullable=True),
    )
    op.create_index("ix_parking_transactions_gate_id", "parking_transactions", ["gate_id"])

    # Migrate existing transactions — IN gates
    op.execute("""
        UPDATE parking_transactions t
        SET gate_id = g.id
        FROM gates g
        WHERE t.gate_in_id IS NOT NULL
          AND g.direction = 'IN'
          AND g.code = (SELECT code FROM gate_ins WHERE id = t.gate_in_id)
    """)

    # Migrate existing transactions — OUT gates
    op.execute("""
        UPDATE parking_transactions t
        SET gate_id = g.id
        FROM gates g
        WHERE t.gate_out_id IS NOT NULL
          AND g.direction = 'OUT'
          AND g.code = (SELECT code FROM gate_outs WHERE id = t.gate_out_id)
    """)

    # ── 8. Drop old tables (after verification) ────────────────────────
    # NOTE: Commented out during transition; uncomment after testing
    # op.drop_table("gate_ins")
    # op.drop_table("gate_outs")
    # op.drop_column("parking_transactions", "gate_in_id")
    # op.drop_column("parking_transactions", "gate_out_id")


def downgrade() -> None:
    # Reverse operations
    # Restore old tables would require recreating them from backup
    # For safety, this downgrade only removes new structures

    # Remove gate_id from parking_transactions
    op.drop_index("ix_parking_transactions_gate_id", table_name="parking_transactions")
    op.drop_column("parking_transactions", "gate_id")

    # Remove pos_id from printers (if table exists)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "printers" in inspector.get_table_names():
        if "ix_printers_pos_id" in [i["name"] for i in inspector.get_indexes("printers")]:
            op.drop_index("ix_printers_pos_id", table_name="printers")
        if "pos_id" in [c["name"] for c in inspector.get_columns("printers")]:
            op.drop_column("printers", "pos_id")

    # Drop unified tables
    op.drop_table("gates")
    op.drop_table("pos")
    op.drop_table("cameras")
