"""Unified daemon CLI entry point.

Launches GateInDaemon for IN gates. OUT gates are operator-attended:
booth_bridge owns serial relay + readers, no autonomous daemon runs.

Usage:
    python -m daemons.cli --gate-id GIN01
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from pathlib import Path

# Ensure project root is on path when run as module
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.config import get_settings
from shared.logging import configure_logging, get_logger

logger = get_logger("daemon_cli")


async def _build_config(session: AsyncSession, gate_code: str) -> dict:
    """Fetch gate config from DB and flatten into dict for daemon consumption."""
    # Import here to avoid circulars and ensure models are registered
    from api.app.models.gate import Gate

    result = await session.execute(select(Gate).where(Gate.code == gate_code))
    gate = result.scalar_one_or_none()

    if gate is None:
        raise RuntimeError(f"Gate with code '{gate_code}' not found in database")

    # Base config from flat columns
    config = {
        "id": gate.id,
        "name": gate.name,
        "code": gate.code,
        "direction": gate.direction,
        "area_parkir_id": gate.area_parkir_id,
        "pos_id": gate.pos_id,
        "protocol": gate.protocol,
        "controller_host": gate.controller_host,
        "controller_port": gate.controller_port,
        "controller_device": gate.controller_device,
        "controller_baudrate": gate.controller_baudrate,
        "has_close_sensor": gate.has_close_sensor,
        "gate_close_duration_ms": gate.gate_close_duration_ms,
        "relay_mode": gate.relay_mode,
        "gate_open_timeout_s": gate.gate_open_timeout_s,
        "sensor_stuck_s": gate.sensor_stuck_s,
        "is_active": gate.is_active,
        "is_online": gate.is_online,
    }

    # Merge hardware_config JSONB (direction-specific settings)
    hw = gate.hardware_config or {}
    config["hardware_config"] = hw

    # Flatten common hardware_config values for backward compatibility
    config["gate_mode"] = hw.get("gate_mode", "CASH")
    config["emoney_minimum_balance"] = hw.get("emoney_minimum_balance", 10000)
    config["print_decision_timeout_seconds"] = hw.get("print_decision_timeout_seconds", 10)
    config["payment_timeout_seconds"] = hw.get("payment_timeout_seconds", 120)
    config["open_command"] = hw.get("open_command")
    config["close_command"] = hw.get("close_command")
    config["pulse_duration_ms"] = hw.get("pulse_duration_ms")

    logger.info(
        "gate_config_loaded",
        gate_id=gate_code,
        direction=gate.direction,
        protocol=gate.protocol,
        host=gate.controller_host,
        port=gate.controller_port,
    )
    return config


async def _run_daemon(gate_code: str) -> None:
    """Lookup gate, instantiate daemon, and run until shutdown."""
    settings = get_settings()
    configure_logging()

    # Independent DB engine for daemon (never import api.database)
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=2,
        max_overflow=2,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    config: dict | None = None
    direction: str | None = None

    async with session_factory() as session:
        config = await _build_config(session, gate_code)
        direction = config["direction"]

    await engine.dispose()

    # Instantiate correct daemon based on direction
    if direction == "IN":
        from daemons.gate_in import GateInDaemon

        daemon = GateInDaemon(gate_id=gate_code, config=config)
    elif direction == "OUT":
        # OUT gates are operator-attended: booth_bridge owns serial relay + readers,
        # POS drives open/close directly. No autonomous daemon needed.
        logger.info("gate_out_daemon_skipped_attended_mode", gate_id=gate_code)
        return
    else:
        raise RuntimeError(f"Unknown gate direction: {direction}")

    # Signal handling
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def _on_signal(sig: int) -> None:
        logger.info("shutdown_signal_received", signal=signal.Signals(sig).name)
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: _on_signal(s))

    # Run daemon
    daemon_task = asyncio.create_task(daemon.run())
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    done, pending = await asyncio.wait(
        [daemon_task, shutdown_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # Cancel remaining and graceful stop
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

    if not daemon_task.done():
        await daemon.stop()

    logger.info("daemon_shutdown_complete", gate_id=gate_code)


def main() -> int:
    parser = argparse.ArgumentParser(description="E-Parking v2 Gate Daemon Runner")
    parser.add_argument("--gate-id", required=True, help="Gate code from database (e.g. GIN01)")
    args = parser.parse_args()

    try:
        asyncio.run(_run_daemon(args.gate_id))
    except RuntimeError as e:
        logger.error("daemon_fatal_error", error=str(e))
        return 1
    except Exception as e:
        logger.exception("daemon_uncaught_exception")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
