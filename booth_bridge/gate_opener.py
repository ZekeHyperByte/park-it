"""Local serial relay gate opener.

Writes open hex to the serial relay, sleeps, optionally writes close hex.
Mirrors legacy parking-system/gate_out.py behavior. Used by booth_bridge
for autonomous exit flows (UHF auto-success, eMoney auto-success).
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import serial

from shared.logging import get_logger

logger = get_logger("booth_gate_opener")


class GateOpener:
    """Holds gate relay config; opens + auto-closes the boom barrier."""

    def __init__(self, gate_config: dict[str, Any]) -> None:
        hw = gate_config.get("hardware_config") or {}
        self.gate_id: str = gate_config.get("code", "")
        self.gate_db_id: int = gate_config.get("id", 0)
        self.device: str = gate_config.get("controller_device") or hw.get("device", "/dev/ttyUSB0")
        self.baudrate: int = int(gate_config.get("controller_baudrate") or hw.get("baudrate", 9600))
        self.open_command_hex: str = hw.get("open_command") or gate_config.get("open_command", "")
        self.close_command_hex: str = hw.get("close_command") or gate_config.get("close_command", "")
        self.close_delay_s: float = float(hw.get("close_delay_seconds", 3))
        self._lock = asyncio.Lock()

    def _decode_hex(self, value: str) -> bytes:
        if not value:
            return b""
        stripped = value.replace(" ", "").replace("\\x", "")
        if all(c in "0123456789abcdefABCDEF" for c in stripped) and len(stripped) % 2 == 0:
            try:
                return bytes.fromhex(stripped)
            except ValueError:
                pass
        return value.encode()

    def is_present(self) -> bool:
        """True if the configured serial device path exists on disk."""
        return bool(self.device) and os.path.exists(self.device)

    async def open(self) -> bool:
        """Open boom barrier, schedule auto-close. Returns True on serial write success."""
        async with self._lock:
            return await asyncio.to_thread(self._open_sync)

    def _open_sync(self) -> bool:
        if not self.open_command_hex:
            logger.error("gate_open_no_command", gate_id=self.gate_id)
            return False
        try:
            ser = serial.Serial(self.device, self.baudrate, timeout=1)
        except Exception as e:
            logger.error("gate_serial_open_failed", gate_id=self.gate_id, error=str(e))
            return False

        try:
            open_bytes = self._decode_hex(self.open_command_hex)
            ser.write(open_bytes)
            logger.info("gate_opened", gate_id=self.gate_id, device=self.device)

            if self.close_command_hex and self.close_delay_s > 0:
                time.sleep(self.close_delay_s)
                close_bytes = self._decode_hex(self.close_command_hex)
                ser.write(close_bytes)
                logger.info("gate_closed", gate_id=self.gate_id, after_s=self.close_delay_s)
            return True
        except Exception as e:
            logger.error("gate_write_failed", gate_id=self.gate_id, error=str(e))
            return False
        finally:
            try:
                ser.close()
            except Exception:
                pass
