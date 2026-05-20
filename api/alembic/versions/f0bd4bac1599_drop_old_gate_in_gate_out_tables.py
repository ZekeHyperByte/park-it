"""drop old gate_in gate_out tables

Revision ID: f0bd4bac1599
Revises: f7a2b8c9d0e1
Create Date: 2026-04-27 16:35:07.633117

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0bd4bac1599"
down_revision: Union[str, None] = "f7a2b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ── 1. Migrate any remaining gate_ins data to unified gates ────────
    if "gate_ins" in inspector.get_table_names():
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
            ON CONFLICT (code) DO NOTHING
        """)

    # ── 2. Migrate any remaining gate_outs data to unified gates ───────
    if "gate_outs" in inspector.get_table_names():
        # Ensure POS records exist for gate_outs that don't have one yet
        op.execute("""
            INSERT INTO pos (name, code, ip_address, is_active, created_at, updated_at)
            SELECT
                name || ' Booth', code || '_POS', NULL, is_active, created_at, updated_at
            FROM gate_outs
            WHERE code || '_POS' NOT IN (SELECT code FROM pos)
            ON CONFLICT (code) DO NOTHING
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
            LEFT JOIN pos p ON p.code = g.code || '_POS'
            ON CONFLICT (code) DO NOTHING
        """)

    # ── 3. Update ParkingTransaction foreign keys ──────────────────────
    if "gate_ins" in inspector.get_table_names():
        op.execute("""
            UPDATE parking_transactions t
            SET gate_in_id = g.id
            FROM gates g
            WHERE t.gate_in_id IS NOT NULL
              AND g.direction = 'IN'
              AND g.code = (SELECT code FROM gate_ins WHERE id = t.gate_in_id)
        """)

    if "gate_outs" in inspector.get_table_names():
        op.execute("""
            UPDATE parking_transactions t
            SET gate_out_id = g.id
            FROM gates g
            WHERE t.gate_out_id IS NOT NULL
              AND g.direction = 'OUT'
              AND g.code = (SELECT code FROM gate_outs WHERE id = t.gate_out_id)
        """)

    # ── 4. Update AbandonedVehicleLog foreign keys ─────────────────────
    if "gate_outs" in inspector.get_table_names():
        op.execute("""
            UPDATE abandoned_vehicle_logs l
            SET gate_out_id = g.id
            FROM gates g
            WHERE l.gate_out_id IS NOT NULL
              AND g.direction = 'OUT'
              AND g.code = (SELECT code FROM gate_outs WHERE id = l.gate_out_id)
        """)

    # ── 5. Drop old foreign key constraints ────────────────────────────
    def _drop_fk_if_exists(table: str, column: str, ref_table: str) -> None:
        """Drop auto-generated FK constraint if it exists."""
        fks = inspector.get_foreign_keys(table)
        for fk in fks:
            if fk.get("referred_table") == ref_table and column in fk.get("constrained_columns", []):
                op.drop_constraint(fk["name"], table, type_="foreignkey")
                break

    if "parking_transactions" in inspector.get_table_names():
        _drop_fk_if_exists("parking_transactions", "gate_in_id", "gate_ins")
        _drop_fk_if_exists("parking_transactions", "gate_out_id", "gate_outs")

    if "abandoned_vehicle_logs" in inspector.get_table_names():
        _drop_fk_if_exists("abandoned_vehicle_logs", "gate_out_id", "gate_outs")

    # ── 6. Create new foreign key constraints to gates.id ──────────────
    if "parking_transactions" in inspector.get_table_names():
        op.create_foreign_key(
            "fk_parking_transactions_gate_in",
            "parking_transactions",
            "gates",
            ["gate_in_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_parking_transactions_gate_out",
            "parking_transactions",
            "gates",
            ["gate_out_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if "abandoned_vehicle_logs" in inspector.get_table_names():
        op.create_foreign_key(
            "fk_abandoned_vehicle_logs_gate_out",
            "abandoned_vehicle_logs",
            "gates",
            ["gate_out_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # ── 7. Drop unused gate_id column from parking_transactions ────────
    if "parking_transactions" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("parking_transactions")]
        if "gate_id" in cols:
            # Drop index first if it exists
            idxs = [i["name"] for i in inspector.get_indexes("parking_transactions")]
            if "ix_parking_transactions_gate_id" in idxs:
                op.drop_index("ix_parking_transactions_gate_id", table_name="parking_transactions")
            op.drop_column("parking_transactions", "gate_id")

    # ── 8. Drop old tables ─────────────────────────────────────────────
    if "gate_ins" in inspector.get_table_names():
        op.drop_table("gate_ins")
    if "gate_outs" in inspector.get_table_names():
        op.drop_table("gate_outs")


def downgrade() -> None:
    """Downgrade is intentionally minimal — old tables would need to be
    recreated from scratch. This migration is a one-way cleanup."""
    pass
