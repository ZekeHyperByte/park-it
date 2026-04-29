# Hardware Configuration & Booth Architecture Migration Plan

> **Date:** 2026-04-27  
> **Status:** Design Complete — Ready for Implementation  
> **Impact:** Critical — Resolves fundamental architecture mismatch between v2 and production reality

---

## Executive Summary

v2's current hardware configuration model assumes a **"gate-centric, controller-passthrough"** world where all peripherals connect to the gate controller. Production reality is **"gate + booth"** where:

- **Gate-In**: Manless — driver interacts directly with gate peripherals (buttons, RFID, ticket printer)
- **Gate-Out**: Booth-operated — operator sits at a POS booth with serial/USB devices (e-money reader, receipt printer, barcode scanner, cash drawer) that the web browser cannot access

This migration unifies `GateIn`/`GateOut` into a single `Gate` entity, introduces a `Pos` (booth) model, extracts peripherals into proper entities, and restores the missing booth WebSocket bridge architecture from v1.

---

## Current State (v2) — Problems

### Database Schema Issues

| Issue | Current v2 | Production Reality |
|-------|-----------|-------------------|
| **No Booth concept** | `GateOut.emoney_reader_id` assumes controller passthrough | Booth PC has serial/USB e-money reader, receipt printer, barcode scanner |
| **Printer duplication** | Printer fields on `GateIn` (7 columns) + `GateOut` (7 columns) + separate `Printer` table | One receipt printer per booth (POS), one ticket printer per gate-in |
| **Camera is a string** | `camera_url` string column on gate rows | Camera is a proper entity with RTSP URL, credentials, health status |
| **Gate mode is single-choice** | `GateIn.gate_mode: Enum(CASH, RFID, EMONEY)` | Gate-in must auto-detect ALL methods concurrently (button, RFID, e-money) |
| **Overwhelming gate modal** | 25+ fields always visible in `device.vue` | Need toggle-per-peripheral UI |
| **No `Pos` model** | Missing entirely | v1 had `Pos` with `ip_address`, `printer_id`, linked to `GateOut` via `pos_id` |

### Architecture Mismatch

```
v2 Assumption:                          Reality:
┌──────────┐                           ┌──────────────┐
│ GateOut  │──► Controller             │   GateOut    │──► Controller (serial)
│          │    (e-money passthrough)  │              │    (barrier only)
└──────────┘                           └──────────────┘
                                              │
                                        ┌──────────────┐
                                        │  Booth (Pos) │◄── E-Money reader (serial)
                                        │   PC/Web UI  │◄── Receipt printer
                                        │              │◄── Barcode scanner
                                        └──────────────┘    Cash drawer
```

### Code Issues

1. **`gate_out.py` daemon** assumes e-money reader connects through controller (`ControllerPassthroughTransport`) — wrong for booth setup
2. **`device.vue`** shows 25 fields in one modal with no conditional visibility
3. **No WebSocket bridge** for booth serial devices (v1 had `gate_out.py` on port 5678)
4. **Frontend `gate.js`** store assumes all payment events come from gate daemon — booth e-money needs different flow

---

## Target Architecture

### Mental Model

```
PHYSICAL WORLD:

GATE-IN (Manless):
  Controller ──► Barrier, Loops, LED, Audio, Buttons
         │
         ├──► RFID Reader (Wiegand) — OPTIONAL
         ├──► Ticket Printer (controller passthrough) — OPTIONAL
         ├──► E-Money Reader (controller passthrough) — OPTIONAL
         └──► Camera (network)

GATE-OUT (Booth-operated):
  Controller ──► Barrier, Loops, LED, Audio
         │
         └──► Camera (network)
  
  Booth PC ──► E-Money Reader (serial/USB) — OPTIONAL
         ├──► Receipt Printer (serial/USB/network) — OPTIONAL
         ├──► Barcode Scanner (USB HID)
         ├──► Cash Drawer (USB/signal)
         └──► Running Text Display (serial) — OPTIONAL

GATE-OUT (Manless — future):
  Controller ──► Barrier, Loops, LED, Audio
         │
         ├──► E-Money Reader (controller passthrough)
         └──► Camera (network)
```

### Data Model

```
┌─────────────────────────────────────────────────────────────────┐
│                          Gate                                   │
├─────────────────────────────────────────────────────────────────┤
│ id, name, code, direction (IN/OUT), protocol, controller_*      │
│ is_active, hardware_config (JSONB)                              │
│                                                                 │
│ hardware_config:                                                │
│   {                                                             │
│     "gate_close_duration_ms": 5000,                             │
│     "has_close_sensor": true,                                   │
│     "relay_mode": "DUAL",                                       │
│     "gate_open_timeout_s": 10,                                  │
│     "sensor_stuck_s": 30,                                       │
│     "rfid": {"enabled": true, "wiegand_channel": "W"},          │
│     "ticket_printer": {"enabled": true, "printer_id": 5},       │
│     "emoney": {"enabled": true, "minimum_balance": 10000},      │
│     "camera": {"enabled": true, "camera_id": 1},                │
│     "audio": {"enabled": true, "module": "controller"},         │
│     "led": {"enabled": true, "module": "controller"}            │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:1 (OUT gates only)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Pos (Booth)                             │
├─────────────────────────────────────────────────────────────────┤
│ id, name, ip_address, is_active                                 │
│                                                                 │
│ booth_peripherals (JSONB):                                      │
│   {                                                             │
│     "emoney_reader": {"enabled": true, "reader_id": 3},         │
│     "receipt_printer": {"enabled": true, "printer_id": 7},      │
│     "barcode_scanner": {"enabled": true},                       │
│     "cash_drawer": {"enabled": true},                           │
│     "running_text": {"enabled": true, "device": "/dev/ttyUSB1"} │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Entities                            │
├─────────────────────────────────────────────────────────────────┤
│  Printer          EmoneyReader          Camera                  │
│  ─────────        ─────────────         ──────                  │
│  id               id                    id                      │
│  name             name                  name                    │
│  mode             serial_port           rtsp_url                │
│  ip_address       baudrate              snapshot_url            │
│  serial_device    mid/tid/init_key      username/password       │
│  paper_*          is_active             is_active               │
│  is_active                                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Schema Migration (Week 1)

### Task 1.1: Create New Tables

**Files:**
- Create: `api/app/models/gate.py`
- Create: `api/app/models/pos.py`
- Create: `api/app/models/camera.py`
- Create: `api/alembic/versions/2026_04_27_unified_gate_and_pos.py`

**Step 1: Write Alembic migration**

```python
"""Unified Gate and Pos (booth) architecture.

Revision ID: 2026_04_27_unified_gate_and_pos
Revises: <previous_head>
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_04_27_unified_gate_and_pos"
down_revision: Union[str, None] = "<previous_head>"  # TODO: set actual
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 3. Create unified Gate table ───────────────────────────────────
    op.create_table(
        "gates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("direction", sa.String(10), nullable=False),  # 'IN' or 'OUT'
        sa.Column("area_parkir_id", sa.BigInteger(), sa.ForeignKey("area_parkir.id"), nullable=True),
        sa.Column("pos_id", sa.BigInteger(), sa.ForeignKey("pos.id"), nullable=True),  # OUT gates only
        # Controller connection
        sa.Column("protocol", sa.String(20), nullable=False, server_default="compass"),
        sa.Column("controller_host", sa.String(100), nullable=True),
        sa.Column("controller_port", sa.Integer(), nullable=True),
        sa.Column("controller_device", sa.String(100), nullable=True),  # for serial protocol
        sa.Column("controller_baudrate", sa.Integer(), nullable=True),   # for serial protocol
        # Hardware settings
        sa.Column("has_close_sensor", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("gate_close_duration_ms", sa.Integer(), nullable=False, server_default=sa.text("5000")),
        sa.Column("relay_mode", sa.String(20), nullable=False, server_default="SINGLE"),
        sa.Column("gate_open_timeout_s", sa.Integer(), nullable=True),
        sa.Column("sensor_stuck_s", sa.Integer(), nullable=True),
        # Peripherals config (JSONB)
        sa.Column("hardware_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_heartbeat", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
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
                'ticket_printer', CASE WHEN printer_name IS NOT NULL THEN jsonb_build_object('enabled', true, 'printer_name', printer_name, 'printer_type', printer_type) ELSE '{}'::jsonb END,
                'camera', CASE WHEN camera_url IS NOT NULL THEN jsonb_build_object('enabled', true, 'camera_url', camera_url) ELSE '{}'::jsonb END,
                'audio_module', audio_module,
                'led_display', led_display
            ),
            is_active, is_online, last_heartbeat,
            created_at, updated_at
        FROM gate_ins
    """)

    # ── 5. Migrate data from GateOut ───────────────────────────────────
    # First create Pos records for existing GateOuts that had pos-like data
    # Note: v2 didn't have Pos, so we create default Pos per GateOut
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
                'receipt_printer', CASE WHEN g.printer_name IS NOT NULL THEN jsonb_build_object('enabled', true, 'printer_name', g.printer_name, 'printer_type', g.printer_type) ELSE '{}'::jsonb END,
                'camera', CASE WHEN g.camera_url IS NOT NULL THEN jsonb_build_object('enabled', true, 'camera_url', g.camera_url) ELSE '{}'::jsonb END,
                'audio_module', g.audio_module,
                'led_display', g.led_display,
                'uhf_reader', CASE WHEN g.uhf_reader_host IS NOT NULL THEN jsonb_build_object('enabled', true, 'host', g.uhf_reader_host, 'port', g.uhf_reader_port) ELSE '{}'::jsonb END
            ),
            g.is_active, g.is_online, g.last_heartbeat,
            g.created_at, g.updated_at
        FROM gate_outs g
        JOIN pos p ON p.code = g.code || '_POS'
    """)

    # ── 6. Update Printer table ────────────────────────────────────────
    # Add pos_id column, keep gate_id for backward compat during transition
    op.add_column("printers", sa.Column("pos_id", sa.BigInteger(), sa.ForeignKey("pos.id"), nullable=True))
    op.create_index("ix_printers_pos_id", "printers", ["pos_id"])

    # ── 7. Update ParkingTransaction foreign keys ──────────────────────
    # Add gate_id column (will replace gate_in_id/gate_out_id)
    op.add_column("parking_transactions", sa.Column("gate_id", sa.BigInteger(), sa.ForeignKey("gates.id"), nullable=True))
    op.create_index("ix_parking_transactions_gate_id", "parking_transactions", ["gate_id"])

    # Migrate existing transactions
    op.execute("""
        UPDATE parking_transactions t
        SET gate_id = g.id
        FROM gates g
        WHERE t.gate_in_id IS NOT NULL AND g.direction = 'IN' AND g.code = (SELECT code FROM gate_ins WHERE id = t.gate_in_id)
    """)
    op.execute("""
        UPDATE parking_transactions t
        SET gate_id = g.id
        FROM gates g
        WHERE t.gate_out_id IS NOT NULL AND g.direction = 'OUT' AND g.code = (SELECT code FROM gate_outs WHERE id = t.gate_out_id)
    """)

    # ── 8. Drop old tables (after verification) ────────────────────────
    # NOTE: Comment these out during development; uncomment after testing
    # op.drop_table("gate_ins")
    # op.drop_table("gate_outs")
    # op.drop_column("parking_transactions", "gate_in_id")
    # op.drop_column("parking_transactions", "gate_out_id")


def downgrade() -> None:
    # Reverse operations (detailed in implementation)
    pass
```

**Step 2: Create Gate model**

```python
# api/app/models/gate.py
"""Unified Gate model replacing GateIn and GateOut."""

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class Gate(Base, IntPKMixin, TimestampMixin):
    """Entry or exit gate with configurable peripherals."""

    __tablename__ = "gates"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # 'IN' or 'OUT'
    area_parkir_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("area_parkir.id"), nullable=True
    )
    pos_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pos.id"), nullable=True
    )  # Only for OUT gates

    # Controller connection
    protocol: Mapped[str] = mapped_column(String(20), default="compass", nullable=False)
    controller_host: Mapped[str | None] = mapped_column(String(100), nullable=True)
    controller_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    controller_device: Mapped[str | None] = mapped_column(String(100), nullable=True)
    controller_baudrate: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Hardware settings
    has_close_sensor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gate_close_duration_ms: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    relay_mode: Mapped[str] = mapped_column(String(20), default="SINGLE", nullable=False)
    gate_open_timeout_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sensor_stuck_s: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Peripherals configuration (JSONB)
    hardware_config: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_heartbeat: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    area_parkir: Mapped["AreaParkir | None"] = relationship("AreaParkir", lazy="selectin")
    pos: Mapped["Pos | None"] = relationship("Pos", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Gate(id={self.id}, name={self.name}, direction={self.direction})>"

    @property
    def is_entry(self) -> bool:
        return self.direction == "IN"

    @property
    def is_exit(self) -> bool:
        return self.direction == "OUT"

    def get_peripheral(self, key: str) -> dict:
        """Get peripheral config by key. Returns empty dict if not configured."""
        return self.hardware_config.get(key, {})

    def is_peripheral_enabled(self, key: str) -> bool:
        """Check if a peripheral is enabled."""
        return self.get_peripheral(key).get("enabled", False)
```

**Step 3: Create Pos model**

```python
# api/app/models/pos.py
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

    # Booth peripherals configuration
    booth_peripherals: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    gates: Mapped[list["Gate"]] = relationship("Gate", back_populates="pos")
    printer: Mapped["Printer | None"] = relationship("Printer", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Pos(id={self.id}, name={self.name}, ip={self.ip_address})>"

    def get_peripheral(self, key: str) -> dict:
        return self.booth_peripherals.get(key, {})

    def is_peripheral_enabled(self, key: str) -> bool:
        return self.get_peripheral(key).get("enabled", False)
```

**Step 4: Create Camera model**

```python
# api/app/models/camera.py
"""Camera entity for RTSP surveillance."""

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class Camera(Base, IntPKMixin, TimestampMixin):
    """RTSP camera configuration."""

    __tablename__ = "cameras"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rtsp_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    snapshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[str | None] = mapped_column(String(20), default="rtsp", nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Camera(id={self.id}, name={self.name})>"
```

**Step 5: Update Printer model**

```python
# api/app/models/printer.py
"""Printer model with paper counter and location tracking."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from api.app.models.base import Base, IntPKMixin, TimestampMixin


class Printer(Base, IntPKMixin, TimestampMixin):
    """A thermal printer (entry ticket or receipt)."""

    __tablename__ = "printers"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(
        String(30), default="CONTROLLER_PASSTHROUGH", nullable=False
    )  # CONTROLLER_PASSTHROUGH, NETWORK, SERIAL

    # Connection
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    serial_device: Mapped[str | None] = mapped_column(String(100), nullable=True)
    baudrate: Mapped[int] = mapped_column(Integer, default=9600, nullable=False)

    # Location (mutually exclusive)
    pos_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pos.id"), nullable=True
    )  # For receipt printers at booth

    # Paper counter
    paper_remaining: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    paper_capacity: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    last_refilled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Printer(id={self.id}, name={self.name}, mode={self.mode})>"
```

**Step 6: Run migration**

```bash
# Backup database first
pg_dump -h localhost -U parking parking > parking_backup_$(date +%Y%m%d_%H%M%S).sql

# Run migration
alembic upgrade head

# Verify
psql -h localhost -U parking -c "\dt"
psql -h localhost -U parking -c "SELECT * FROM gates LIMIT 5"
```

**Step 7: Commit**

```bash
git add api/app/models/gate.py api/app/models/pos.py api/app/models/camera.py
 git add api/app/models/printer.py
 git add api/alembic/versions/2026_04_27_unified_gate_and_pos.py
git commit -m "feat(schema): add unified Gate, Pos, Camera models

- Replace GateIn/GateOut with single Gate table (direction: IN/OUT)
- Add Pos (booth) model for exit operator stations
- Add Camera as proper entity
- Update Printer with pos_id for booth receipt printers
- Migration preserves all existing data in hardware_config JSONB"
```

---

## Phase 2: API Routes (Week 1-2)

### Task 2.1: Create Gate Routes (Unified)

**Files:**
- Create: `api/app/routes/gates_unified.py`
- Delete (after transition): `api/app/routes/gates.py`

**Step 1: Write unified gate routes**

```python
# api/app/routes/gates_unified.py
"""Unified gate management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.gate import Gate
from api.app.schemas.common import SuccessResponse
from api.app.schemas.gate import GateCreate, GateResponse, GateUpdate
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("gate_routes")
router = APIRouter(prefix="/gates", tags=["Gates"])


@router.get("", response_model=list[GateResponse])
async def list_gates(
    direction: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[GateResponse]:
    """List all gates, optionally filtered by direction."""
    query = select(Gate)
    if direction:
        query = query.where(Gate.direction == direction.upper())
    result = await db.execute(query)
    gates = result.scalars().all()
    return [GateResponse.model_validate(g) for g in gates]


@router.post("", response_model=GateResponse, status_code=status.HTTP_201_CREATED)
async def create_gate(
    data: GateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateResponse:
    """Create a new gate (entry or exit)."""
    # Validate: OUT gates should have pos_id if booth-operated
    if data.direction == "OUT" and data.pos_id is None:
        # Allow manless gates without pos
        pass

    gate = Gate(**data.model_dump())
    db.add(gate)
    await db.commit()
    await db.refresh(gate)
    logger.info("gate_created", gate_id=gate.id, code=gate.code, direction=gate.direction)
    return GateResponse.model_validate(gate)


@router.get("/{gate_id}", response_model=GateResponse)
async def get_gate(
    gate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateResponse:
    """Get gate by ID."""
    gate = await db.get(Gate, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    return GateResponse.model_validate(gate)


@router.patch("/{gate_id}", response_model=GateResponse)
async def update_gate(
    gate_id: int,
    data: GateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> GateResponse:
    """Update gate configuration."""
    gate = await db.get(Gate, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")

    update_data = data.model_dump(exclude_unset=True)

    # Validate direction-specific fields
    if "hardware_config" in update_data:
        hw = update_data["hardware_config"]
        if gate.direction == "IN":
            # IN gates can have: rfid, ticket_printer, emoney, camera, audio, led
            pass
        elif gate.direction == "OUT":
            # OUT gates can have: receipt_printer, camera, audio, led, uhf_reader
            pass

    for field, value in update_data.items():
        setattr(gate, field, value)

    await db.commit()
    await db.refresh(gate)
    logger.info("gate_updated", gate_id=gate.id)
    return GateResponse.model_validate(gate)


@router.delete("/{gate_id}", response_model=SuccessResponse)
async def delete_gate(
    gate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete gate."""
    gate = await db.get(Gate, gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate not found")
    await db.delete(gate)
    await db.commit()
    logger.info("gate_deleted", gate_id=gate_id)
    return SuccessResponse(message="Gate deleted")
```

**Step 2: Create schemas**

```python
# api/app/schemas/gate.py
"""Pydantic schemas for unified Gate model."""

from pydantic import BaseModel, Field


class PeripheralConfig(BaseModel):
    """Base peripheral configuration."""

    enabled: bool = False


class RfidConfig(PeripheralConfig):
    """RFID reader configuration."""

    wiegand_channel: str = "W"  # W or X


class PrinterConfig(PeripheralConfig):
    """Printer configuration reference."""

    printer_id: int | None = None


class EmoneyConfig(PeripheralConfig):
    """E-money configuration for gate-in."""

    minimum_balance: int = 10000


class CameraConfig(PeripheralConfig):
    """Camera configuration reference."""

    camera_id: int | None = None


class UhfReaderConfig(PeripheralConfig):
    """UHF RFID reader for gate-out."""

    host: str | None = None
    port: int | None = None


class HardwareConfig(BaseModel):
    """Complete hardware configuration for a gate."""

    gate_close_duration_ms: int = 5000
    has_close_sensor: bool = False
    relay_mode: str = "SINGLE"
    gate_open_timeout_s: int | None = 10
    sensor_stuck_s: int | None = 30

    # Peripherals (all optional, enabled=false by default)
    rfid: RfidConfig = Field(default_factory=RfidConfig)
    ticket_printer: PrinterConfig = Field(default_factory=PrinterConfig)
    emoney: EmoneyConfig = Field(default_factory=EmoneyConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    audio: PeripheralConfig = Field(default_factory=PeripheralConfig)
    led: PeripheralConfig = Field(default_factory=PeripheralConfig)
    uhf_reader: UhfReaderConfig = Field(default_factory=UhfReaderConfig)
    receipt_printer: PrinterConfig = Field(default_factory=PrinterConfig)


class GateBase(BaseModel):
    """Base gate fields."""

    name: str
    code: str
    direction: str = Field(..., pattern="^(IN|OUT)$")
    area_parkir_id: int | None = None
    pos_id: int | None = None
    protocol: str = "compass"
    controller_host: str | None = None
    controller_port: int | None = None
    controller_device: str | None = None
    controller_baudrate: int | None = None
    has_close_sensor: bool = False
    gate_close_duration_ms: int = 5000
    relay_mode: str = "SINGLE"
    hardware_config: HardwareConfig = Field(default_factory=HardwareConfig)
    is_active: bool = True


class GateCreate(GateBase):
    """Create gate request."""

    pass


class GateUpdate(BaseModel):
    """Update gate request (all fields optional)."""

    name: str | None = None
    code: str | None = None
    pos_id: int | None = None
    controller_host: str | None = None
    controller_port: int | None = None
    controller_device: str | None = None
    controller_baudrate: int | None = None
    has_close_sensor: bool | None = None
    gate_close_duration_ms: int | None = None
    relay_mode: str | None = None
    hardware_config: HardwareConfig | None = None
    is_active: bool | None = None


class GateResponse(GateBase):
    """Gate response."""

    id: int
    is_online: bool
    last_heartbeat: str | None = None

    model_config = {"from_attributes": True}
```

**Step 3: Create Pos routes**

```python
# api/app/routes/pos.py
"""POS (booth) management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import require_admin
from api.app.models.pos import Pos
from api.app.schemas.common import SuccessResponse
from api.app.schemas.pos import PosCreate, PosResponse, PosUpdate
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("pos_routes")
router = APIRouter(prefix="/pos", tags=["POS / Booth"])


@router.get("", response_model=list[PosResponse])
async def list_pos(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> list[PosResponse]:
    """List all POS booths."""
    result = await db.execute(select(Pos))
    pos_list = result.scalars().all()
    return [PosResponse.model_validate(p) for p in pos_list]


@router.post("", response_model=PosResponse, status_code=status.HTTP_201_CREATED)
async def create_pos(
    data: PosCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> PosResponse:
    """Create a new POS booth."""
    pos = Pos(**data.model_dump())
    db.add(pos)
    await db.commit()
    await db.refresh(pos)
    logger.info("pos_created", pos_id=pos.id, code=pos.code)
    return PosResponse.model_validate(pos)


@router.get("/{pos_id}", response_model=PosResponse)
async def get_pos(
    pos_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> PosResponse:
    """Get POS by ID."""
    pos = await db.get(Pos, pos_id)
    if pos is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POS not found")
    return PosResponse.model_validate(pos)


@router.patch("/{pos_id}", response_model=PosResponse)
async def update_pos(
    pos_id: int,
    data: PosUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> PosResponse:
    """Update POS configuration."""
    pos = await db.get(Pos, pos_id)
    if pos is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POS not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pos, field, value)

    await db.commit()
    await db.refresh(pos)
    logger.info("pos_updated", pos_id=pos.id)
    return PosResponse.model_validate(pos)


@router.delete("/{pos_id}", response_model=SuccessResponse)
async def delete_pos(
    pos_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
) -> SuccessResponse:
    """Delete POS booth."""
    pos = await db.get(Pos, pos_id)
    if pos is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POS not found")
    await db.delete(pos)
    await db.commit()
    logger.info("pos_deleted", pos_id=pos_id)
    return SuccessResponse(message="POS deleted")
```

**Step 4: Register new routes in main.py**

```python
# api/app/main.py (modification)
from api.app.routes import (
    # ... existing imports ...
    gates_unified,  # Add this
    pos,            # Add this
)

# In create_app():
app.include_router(gates_unified.router, prefix="/api")
app.include_router(pos.router, prefix="/api")
```

---

## Phase 3: Frontend Device Page Redesign (Week 2)

### Task 3.1: Rewrite device.vue

**Files:**
- Modify: `frontend/pages/device.vue`

**Step 1: Redesign with unified gate list and peripheral toggles**

```vue
<template>
  <div>
    <h1>Perangkat</h1>
    <p class="text-secondary mb-3">Manajemen gate, booth POS, dan perangkat terkait.</p>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- Gates -->
      <el-tab-pane label="Gates" name="gates">
        <DataTable
          :data="gates"
          :columns="gateColumns"
          :loading="loadingGates"
          @add="openGateModal()"
          @edit="openGateModal"
          @delete="confirmDeleteGate"
        />
      </el-tab-pane>

      <!-- POS Booths -->
      <el-tab-pane label="Booth POS" name="pos">
        <DataTable
          :data="posList"
          :columns="posColumns"
          :loading="loadingPos"
          @add="openPosModal()"
          @edit="openPosModal"
          @delete="confirmDeletePos"
        />
      </el-tab-pane>

      <!-- Cameras -->
      <el-tab-pane label="Kamera" name="cameras">
        <DataTable
          :data="cameras"
          :columns="cameraColumns"
          :loading="loadingCameras"
          @add="openCameraModal()"
          @edit="openCameraModal"
          @delete="confirmDeleteCamera"
        />
      </el-tab-pane>

      <!-- Printers -->
      <el-tab-pane label="Printer" name="printers">
        <DataTable
          :data="printers"
          :columns="printerColumns"
          :loading="loadingPrinters"
          @add="openPrinterModal()"
          @edit="openPrinterModal"
          @delete="confirmDeletePrinter"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- Gate Modal -->
    <CrudModal
      v-model="gateModalVisible"
      :title="gateEditing ? 'Edit Gate' : 'Tambah Gate'"
      :fields="gateFields"
      :initial-data="gateForm"
      :submitting="submitting"
      @submit="saveGate"
    />

    <!-- ... other modals ... -->
  </div>
</template>

<script setup>
// Gate columns
const gateColumns = [
  { prop: 'name', label: 'Nama', sortable: true },
  { prop: 'code', label: 'Kode', width: 120, sortable: true },
  { prop: 'direction', label: 'Arah', width: 80, type: 'enum' },
  { prop: 'protocol', label: 'Protokol', width: 100 },
  { prop: 'controller_host', label: 'Controller', width: 150 },
  { prop: 'peripherals', label: 'Periferal', width: 200 },
  { prop: 'is_active', label: 'Aktif', type: 'boolean', width: 80 },
]

// Gate form fields - CONDITIONAL based on direction
const gateFields = computed(() => {
  const base = [
    { prop: 'name', label: 'Nama', type: 'text', required: true },
    { prop: 'code', label: 'Kode', type: 'text', required: true },
    { prop: 'direction', label: 'Arah', type: 'select', required: true, options: [
      { label: 'Masuk', value: 'IN' },
      { label: 'Keluar', value: 'OUT' },
    ]},
    { prop: 'protocol', label: 'Protokol', type: 'select', required: true, options: [
      { label: 'Compass (TCP)', value: 'compass' },
      { label: 'ENET (TCP)', value: 'enet' },
      { label: 'Serial', value: 'serial' },
    ]},
    { prop: 'controller_host', label: 'Host Controller', type: 'text' },
    { prop: 'controller_port', label: 'Port Controller', type: 'number' },
    { prop: 'has_close_sensor', label: 'Sensor Tutup', type: 'boolean' },
    { prop: 'relay_mode', label: 'Mode Relay', type: 'select', options: [
      { label: 'Single', value: 'SINGLE' },
      { label: 'Dual', value: 'DUAL' },
    ]},
  ]

  // Direction-specific peripherals
  if (gateForm.value.direction === 'IN') {
    base.push(
      { prop: 'hardware_config.rfid.enabled', label: 'RFID Reader', type: 'boolean' },
      { prop: 'hardware_config.ticket_printer.enabled', label: 'Printer Tiket', type: 'boolean' },
      { prop: 'hardware_config.emoney.enabled', label: 'E-Money', type: 'boolean' },
      { prop: 'hardware_config.camera.enabled', label: 'Kamera', type: 'boolean' },
    )
  } else if (gateForm.value.direction === 'OUT') {
    base.push(
      { prop: 'pos_id', label: 'Booth POS', type: 'select', options: posOptions.value },
      { prop: 'hardware_config.uhf_reader.enabled', label: 'UHF Reader', type: 'boolean' },
      { prop: 'hardware_config.camera.enabled', label: 'Kamera', type: 'boolean' },
    )
  }

  base.push({ prop: 'is_active', label: 'Aktif', type: 'boolean' })

  return base
})
</script>
```

---

## Phase 4: Daemon Architecture Update (Week 3)

### Task 4.1: Update Gate-In Daemon for Multi-Method Auto-Detect

**Files:**
- Modify: `daemons/gate_in.py`

**Current problem:** `gate_mode` is single-choice (CASH/RFID/EMONEY)
**Fix:** Remove `gate_mode`, auto-detect all inputs concurrently

```python
# daemons/gate_in.py (key changes)

class GateInDaemon(BaseDaemon):
    def __init__(self, gate_id: str, config: dict[str, Any]) -> None:
        super().__init__(gate_id, config)
        # No more gate_mode — check hardware_config instead
        self.hw = config.get("hardware_config", {})
        self.has_rfid = self.hw.get("rfid", {}).get("enabled", False)
        self.has_ticket_printer = self.hw.get("ticket_printer", {}).get("enabled", False)
        self.has_emoney = self.hw.get("emoney", {}).get("enabled", False)

    async def _handle_stat_response(self, response: bytes) -> None:
        parsed = parse_stat(response)

        if self.state == STATE_IDLE:
            if parsed["in1"]:
                await self._on_vehicle_detected()

        elif self.state == STATE_VEHICLE_PRESENT:
            has_sensor = self.config.get("has_close_sensor", False)
            if has_sensor and parsed["in3"]:
                await self._on_gate_closed()

        elif self.state == STATE_GATE_CLOSED:
            # Auto-detect any input method
            if self.has_rfid and (parsed["wiegand_w"] or parsed["wiegand_x"]):
                await self._on_rfid_card_read(
                    parsed["wiegand_w"] or parsed["wiegand_x"],
                    "W" if parsed["wiegand_w"] else "X"
                )
            elif self.has_emoney and self.gate_mode == GateMode.EMONEY.value:
                # Check PASSTI in background
                pass
            elif parsed["in2"]:
                # Button pressed — cash ticket
                await self._on_ticket_button_pressed()
```

### Task 4.2: Create Booth Bridge Service

**Files:**
- Create: `booth_bridge/main.py`
- Create: `booth_bridge/serial_manager.py`
- Create: `booth_bridge/websocket_server.py`
- Create: `systemd/booth-bridge.service`

**Step 1: Booth bridge main service**

```python
# booth_bridge/main.py
"""Booth Bridge Service — runs on booth PC.

Connects to serial devices (e-money reader, receipt printer, running text)
and exposes them via WebSocket for the POS frontend.

Usage:
    python -m booth_bridge.main --config /etc/parking/booth.json
"""

import argparse
import asyncio
import json
import logging

from booth_bridge.serial_manager import SerialManager
from booth_bridge.websocket_server import WebSocketServer

logger = logging.getLogger("booth_bridge")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/etc/parking/booth.json")
    parser.add_argument("--port", type=int, default=5678)
    args = parser.parse_args()

    # Load booth configuration
    with open(args.config) as f:
        config = json.load(f)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting booth bridge", extra={"port": args.port, "booth": config.get("name")})

    # Initialize serial connections
    serial_manager = SerialManager(config.get("peripherals", {}))
    await serial_manager.start()

    # Start WebSocket server
    ws_server = WebSocketServer(serial_manager, port=args.port)
    await ws_server.start()

    try:
        await asyncio.Event().wait()  # Run forever
    finally:
        await ws_server.stop()
        await serial_manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Serial manager**

```python
# booth_bridge/serial_manager.py
"""Manages serial connections to booth peripherals."""

import asyncio

import serial
import serial_asyncio

from shared.logging import get_logger

logger = get_logger("booth_serial")


class SerialManager:
    """Manages serial connections to booth peripherals."""

    def __init__(self, peripherals: dict) -> None:
        self.peripherals = peripherals
        self._connections: dict[str, serial.Serial] = {}
        self._running = False

    async def start(self) -> None:
        """Open all configured serial connections."""
        self._running = True
        for name, cfg in self.peripherals.items():
            if not cfg.get("enabled"):
                continue
            try:
                conn = serial.Serial(
                    port=cfg["device"],
                    baudrate=cfg.get("baudrate", 38400),
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                )
                self._connections[name] = conn
                logger.info("serial_connected", peripheral=name, device=cfg["device"])
            except Exception as e:
                logger.error("serial_connect_failed", peripheral=name, error=str(e))

    async def stop(self) -> None:
        """Close all serial connections."""
        self._running = False
        for name, conn in self._connections.items():
            try:
                conn.close()
                logger.info("serial_disconnected", peripheral=name)
            except Exception as e:
                logger.error("serial_disconnect_error", peripheral=name, error=str(e))
        self._connections.clear()

    def send(self, peripheral: str, data: bytes) -> bytes:
        """Send data to a peripheral and read response."""
        conn = self._connections.get(peripheral)
        if conn is None:
            raise RuntimeError(f"Peripheral not connected: {peripheral}")
        conn.reset_input_buffer()
        conn.write(data)
        return conn.read(1024)

    def is_connected(self, peripheral: str) -> bool:
        """Check if a peripheral is connected."""
        conn = self._connections.get(peripheral)
        return conn is not None and conn.is_open
```

**Step 3: WebSocket server**

```python
# booth_bridge/websocket_server.py
"""WebSocket server for POS frontend to access serial devices."""

import asyncio
import json

import websockets

from shared.logging import get_logger

logger = get_logger("booth_ws")


class WebSocketServer:
    """WebSocket server exposing serial peripherals to POS frontend."""

    def __init__(self, serial_manager, port: int = 5678) -> None:
        self.serial_manager = serial_manager
        self.port = port
        self._server = None
        self._clients: set = set()

    async def start(self) -> None:
        """Start WebSocket server."""
        self._server = await websockets.serve(self._handle_client, "localhost", self.port)
        logger.info("ws_server_started", port=self.port)

    async def stop(self) -> None:
        """Stop WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("ws_server_stopped")

    async def _handle_client(self, websocket, path):
        """Handle a client connection."""
        self._clients.add(websocket)
        logger.info("client_connected", client=websocket.remote_address)

        try:
            async for message in websocket:
                try:
                    result = await self._process_message(message)
                    await websocket.send(json.dumps(result))
                except Exception as e:
                    logger.error("message_error", error=str(e))
                    await websocket.send(json.dumps({"status": False, "error": str(e)}))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            logger.info("client_disconnected", client=websocket.remote_address)

    async def _process_message(self, message: str) -> dict:
        """Process a command from the POS frontend."""
        cmd = json.loads(message)
        action = cmd.get("action")
        peripheral = cmd.get("peripheral")

        if action == "open_gate":
            # Forward to serial gate controller
            device = cmd.get("device", "/dev/ttyUSB0")
            baudrate = cmd.get("baudrate", 9600)
            open_cmd = cmd.get("open_command", "O1N").encode()
            close_cmd = cmd.get("close_command", "O2N").encode()

            import serial
            ser = serial.Serial(device, baudrate, timeout=1)
            ser.write(open_cmd)
            if close_cmd:
                import time
                time.sleep(1)
                ser.write(close_cmd)
            ser.close()
            return {"status": True, "message": "Gate opened"}

        elif action == "emoney_check_balance":
            # Forward to e-money reader
            from protocols.passti.commands import cmd_check_balance
            frame = cmd_check_balance(timeout_sec=10)
            response = self.serial_manager.send("emoney_reader", frame)
            # Parse response...
            return {"status": True, "data": response.hex()}

        elif action == "emoney_deduct":
            amount = cmd.get("amount", 0)
            from protocols.passti.commands import cmd_deduct
            frame = cmd_deduct(amount, timeout_sec=30)
            response = self.serial_manager.send("emoney_reader", frame)
            return {"status": True, "data": response.hex()}

        elif action == "print_receipt":
            # Forward to receipt printer
            data = cmd.get("data", b"")
            self.serial_manager.send("receipt_printer", data)
            return {"status": True, "message": "Printed"}

        elif action == "running_text":
            text = cmd.get("text", "")
            # Format and send to running text display
            return {"status": True, "message": "Display updated"}

        return {"status": False, "error": f"Unknown action: {action}"}
```

**Step 4: systemd service**

```ini
# systemd/booth-bridge.service
[Unit]
Description=Parking Booth Bridge — Serial to WebSocket
After=network.target

[Service]
Type=simple
User=parking
WorkingDirectory=/opt/parking
Environment=PYTHONPATH=/opt/parking
ExecStart=/opt/parking/.venv/bin/python -m booth_bridge.main --config /etc/parking/booth.json
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Step 5: Booth configuration file**

```json
{
  "name": "Booth Keluar Utama",
  "code": "BOOTH_01",
  "peripherals": {
    "gate_controller": {
      "enabled": true,
      "device": "/dev/ttyUSB0",
      "baudrate": 9600
    },
    "emoney_reader": {
      "enabled": true,
      "device": "/dev/ttyUSB1",
      "baudrate": 38400
    },
    "receipt_printer": {
      "enabled": true,
      "device": "/dev/ttyUSB2",
      "baudrate": 9600
    },
    "running_text": {
      "enabled": true,
      "device": "/dev/ttyUSB3",
      "baudrate": 9600
    }
  }
}
```

---

## Phase 5: Frontend POS Integration (Week 3-4)

### Task 5.1: Update POS Page for Booth E-Money

**Files:**
- Modify: `frontend/pages/index.vue`
- Modify: `frontend/stores/gate.js`

**Step 1: Add booth WebSocket connection**

```javascript
// frontend/pages/index.vue (POS page)

const connectBooth = () => {
  // Connect to booth bridge WebSocket (localhost:5678)
  const ws = new WebSocket(`ws://localhost:5678/`)
  
  ws.onopen = () => {
    console.log('Booth bridge connected')
    boothStore.setConnected(true)
  }
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleBoothMessage(data)
  }
  
  ws.onerror = () => {
    ElMessage.error('KONEKSI KE BOOTH GAGAL')
    boothStore.setConnected(false)
  }
  
  return ws
}

const handleBoothMessage = (data) => {
  if (data.action === 'emoney_deduct_result') {
    if (data.status === 'SUCCESS') {
      gateStore.setEmoneyState('SUCCESS')
      openGate() // Open gate after successful deduct
    } else if (data.status === 'LOST_CONTACT') {
      gateStore.setEmoneyState('LOST_CONTACT')
      ElMessage.warning('Tap kartu lagi untuk koreksi')
    } else {
      gateStore.setEmoneyState('FAILED')
      ElMessage.error(data.error || 'E-Money gagal')
    }
  }
}

const startEmoneyDeduct = () => {
  const tx = gateStore.currentTransaction
  if (!tx?.card_number) {
    ElMessage.warning('Transaksi tidak memiliki nomor kartu e-money')
    return
  }
  
  // Send deduct command to booth bridge
  boothWs.value.send(JSON.stringify({
    action: 'emoney_deduct',
    peripheral: 'emoney_reader',
    amount: tx.tarif,
    expected_card_number: tx.card_number
  }))
  
  gateStore.setEmoneyState('PROCESSING')
}
```

---

## Phase 6: Testing & Validation (Week 4)

### Task 6.1: Migration Verification Checklist

**Database:**
- [ ] All `gate_ins` rows migrated to `gates` with `direction='IN'`
- [ ] All `gate_outs` rows migrated to `gates` with `direction='OUT'`
- [ ] `Pos` records created for each `GateOut`
- [ ] `hardware_config` JSONB populated correctly
- [ ] `parking_transactions` `gate_id` column populated
- [ ] Foreign keys valid (no orphaned references)
- [ ] Indexes created and used in query plans

**API:**
- [ ] `GET /api/gates` returns unified list
- [ ] `GET /api/gates?direction=IN` filters correctly
- [ ] `GET /api/gates?direction=OUT` returns POS-linked gates
- [ ] `POST /api/gates` creates IN and OUT gates
- [ ] `PATCH /api/gates/{id}` updates hardware_config
- [ ] Validation rejects invalid direction-specific fields

**Frontend:**
- [ ] Device page shows unified gate list
- [ ] Gate modal shows direction selector first
- [ ] Peripherals toggle on/off based on direction
- [ ] POS tab shows booth list
- [ ] Camera tab shows camera entities

**Daemons:**
- [ ] Gate-in daemon starts with new config format
- [ ] Auto-detects button/RFID/e-money concurrently
- [ ] Respects `hardware_config.enabled` flags
- [ ] Booth bridge connects to serial devices
- [ ] POS frontend connects to booth bridge WebSocket

**Integration:**
- [ ] End-to-end cash entry → exit flow
- [ ] RFID member entry → exit flow
- [ ] E-money booth entry → exit flow
- [ ] Lost contact recovery at booth
- [ ] Paper counter tracking for booth receipt printer

---

## Rollback Plan

If critical issues arise during migration:

1. **Stop all daemons and booth bridges**
2. **Restore database from backup**
   ```bash
   psql -h localhost -U parking -c "DROP DATABASE parking;"
   psql -h localhost -U postgres -c "CREATE DATABASE parking;"
   psql -h localhost -U parking < parking_backup_YYYYMMDD_HHMMSS.sql
   ```
3. **Revert code changes**
   ```bash
   git reset --hard HEAD~N  # N = number of migration commits
   ```
4. **Restart old daemons**
   ```bash
   sudo systemctl start parking-daemon-gate-in@<name>
   sudo systemctl start parking-daemon-gate-out@<name>
   ```

---

## Appendix A: Hardware Config JSONB Schema

### Gate-In (direction='IN')

```json
{
  "gate_close_duration_ms": 5000,
  "has_close_sensor": false,
  "relay_mode": "SINGLE",
  "gate_open_timeout_s": 10,
  "sensor_stuck_s": 30,
  "rfid": {
    "enabled": true,
    "wiegand_channel": "W"
  },
  "ticket_printer": {
    "enabled": true,
    "printer_id": 5
  },
  "emoney": {
    "enabled": true,
    "minimum_balance": 10000,
    "print_decision_timeout_seconds": 10
  },
  "camera": {
    "enabled": true,
    "camera_id": 1
  },
  "audio": {
    "enabled": true,
    "module": "controller"
  },
  "led": {
    "enabled": true,
    "module": "controller"
  }
}
```

### Gate-Out Booth (direction='OUT')

```json
{
  "gate_close_duration_ms": 5000,
  "has_close_sensor": false,
  "relay_mode": "DUAL",
  "gate_open_timeout_s": 10,
  "sensor_stuck_s": 30,
  "payment_timeout_seconds": 120,
  "camera": {
    "enabled": true,
    "camera_id": 2
  },
  "audio": {
    "enabled": true,
    "module": "controller"
  },
  "led": {
    "enabled": true,
    "module": "controller"
  },
  "uhf_reader": {
    "enabled": false
  }
}
```

### POS Booth Peripherals

```json
{
  "emoney_reader": {
    "enabled": true,
    "reader_id": 3
  },
  "receipt_printer": {
    "enabled": true,
    "printer_id": 7
  },
  "barcode_scanner": {
    "enabled": true
  },
  "cash_drawer": {
    "enabled": true
  },
  "running_text": {
    "enabled": true,
    "device": "/dev/ttyUSB1",
    "baudrate": 9600
  }
}
```

---

## Appendix B: File Changes Summary

### New Files
- `api/app/models/gate.py` — Unified Gate model
- `api/app/models/pos.py` — POS booth model
- `api/app/models/camera.py` — Camera entity
- `api/app/routes/gates_unified.py` — Unified gate routes
- `api/app/routes/pos.py` — POS booth routes
- `api/app/schemas/gate.py` — Gate Pydantic schemas
- `api/app/schemas/pos.py` — POS Pydantic schemas
- `api/alembic/versions/2026_04_27_unified_gate_and_pos.py` — Migration
- `booth_bridge/main.py` — Booth bridge service
- `booth_bridge/serial_manager.py` — Serial device manager
- `booth_bridge/websocket_server.py` — WebSocket server
- `systemd/booth-bridge.service` — systemd unit

### Modified Files
- `api/app/models/printer.py` — Add `pos_id`
- `api/app/models/__init__.py` — Export new models
- `api/app/routes/__init__.py` — Export new routes
- `api/app/main.py` — Register new routers
- `daemons/gate_in.py` — Multi-method auto-detect
- `daemons/gate_out.py` — Remove e-money controller passthrough
- `frontend/pages/device.vue` — Redesigned UI
- `frontend/pages/index.vue` — Booth WebSocket integration
- `frontend/stores/gate.js` — Booth state management
- `shared/events.py` — Add booth events

### Deprecated (After Transition)
- `api/app/models/gate_in.py` — Replaced by Gate
- `api/app/models/gate_out.py` — Replaced by Gate
- `api/app/routes/gates.py` — Replaced by gates_unified
- `api/app/schemas/gate_in.py` — Replaced by gate schema
- `api/app/schemas/gate_out.py` — Replaced by gate schema

---

## Appendix C: Migration Command Reference

```bash
# 1. Backup
pg_dump -h localhost -U parking parking > parking_backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Stop services
sudo systemctl stop parking-api
sudo systemctl stop parking-daemon-gate-in@*
sudo systemctl stop parking-daemon-gate-out@*

# 3. Run migration
alembic upgrade head

# 4. Verify
psql -h localhost -U parking -c "SELECT id, name, direction, code FROM gates ORDER BY direction, id;"
psql -h localhost -U parking -c "SELECT id, name, code, ip_address FROM pos;"

# 5. Deploy booth bridges (on each booth PC)
sudo cp systemd/booth-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable booth-bridge
sudo systemctl start booth-bridge

# 6. Restart API
sudo systemctl start parking-api

# 7. Restart daemons
sudo systemctl start parking-daemon-gate-in@<gate_code>

# 8. Verify frontend loads
# Open browser to http://localhost:3000/device
# Check gates show correctly with peripherals
```

---

*End of Migration Plan*
