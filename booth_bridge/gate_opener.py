"""Local serial relay gate opener.

Writes open hex to the serial relay, sleeps, optionally writes close hex.
Mirrors legacy parking-system/gate_out.py behavior. Used by booth_bridge
for autonomous exit flows (UHF auto-success, eMoney auto-success).
"""

from __future__ import annotations

import asyncio
import contextlib
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

        # Resolve commands at construction time so the tech sees in logs
        # exactly how each gate's open/close string was interpreted. A typo
        # like "*TRIG 1#" (space) decodes as 8 ASCII bytes including the
        # space — the log preview makes that visible before a real tap
        # silently misfires in the field.
        self._open_bytes, open_mode, open_warn = self._decode_command(self.open_command_hex)
        self._close_bytes, close_mode, close_warn = self._decode_command(self.close_command_hex)
        if self.open_command_hex:
            logger.info(
                "gate_open_command_decoded",
                gate_id=self.gate_id,
                mode=open_mode,
                source=self.open_command_hex,
                bytes_hex=self._open_bytes.hex(),
                length=len(self._open_bytes),
            )
            if open_warn:
                logger.warning("gate_open_command_suspicious", gate_id=self.gate_id, warning=open_warn)
        if self.close_command_hex:
            logger.info(
                "gate_close_command_decoded",
                gate_id=self.gate_id,
                mode=close_mode,
                source=self.close_command_hex,
                bytes_hex=self._close_bytes.hex(),
                length=len(self._close_bytes),
            )
            if close_warn:
                logger.warning("gate_close_command_suspicious", gate_id=self.gate_id, warning=close_warn)

    @staticmethod
    def _decode_command(value: str) -> tuple[bytes, str, str | None]:
        """Decode an open/close command into wire bytes.

        Returns ``(bytes, mode, warning)`` where ``mode`` is one of
        ``"empty"``, ``"hex"``, ``"ascii"`` and ``warning`` (when not None)
        flags a likely config typo for the boot log. Decoding never raises:
        the bridge boots even with a broken command so the tech can fix it
        from the admin UI without an SSH session — the warning surfaces in
        the journal instead.
        """
        if not value:
            return b"", "empty", None

        stripped = value.replace(" ", "").replace("\\x", "")
        hex_chars = sum(c in "0123456789abcdefABCDEF" for c in stripped)
        non_hex_chars = len(stripped) - hex_chars

        # Pure hex with even length → decode as hex.
        if non_hex_chars == 0 and len(stripped) > 0 and len(stripped) % 2 == 0:
            try:
                return bytes.fromhex(stripped), "hex", None
            except ValueError:
                # Should not happen given the char filter above, but fall
                # through to ASCII rather than crashing.
                pass

        # Odd-length all-hex is almost certainly a typo (missing digit). Fall
        # back to ASCII but surface the suspicion.
        warning: str | None = None
        if non_hex_chars == 0 and len(stripped) > 0 and len(stripped) % 2 == 1:
            warning = (
                f"value looks like hex but length is odd ({len(stripped)}) — "
                "is a digit missing?"
            )

        # Mixed hex chars + non-hex (e.g. "*TRIG1FF#"): could be a paste
        # accident. Common ASCII relay commands like "*TRIG1#" intentionally
        # mix letters and digits, so don't warn if the value matches a known
        # ASCII relay pattern.
        if hex_chars > 0 and non_hex_chars > 0 and warning is None:
            ascii_relay_like = value[0:1] in ("*", "O", "C") and value.isascii()
            if not ascii_relay_like:
                warning = (
                    "mixed hex/non-hex chars detected — verify this is the "
                    "intended ASCII relay command, not a corrupted hex string."
                )

        return value.encode(), "ascii", warning

    def _decode_hex(self, value: str) -> bytes:
        # Retained for compatibility with any callers that decode ad-hoc; the
        # init path uses _decode_command directly and caches the result.
        decoded, _, _ = self._decode_command(value)
        return decoded

    def is_present(self) -> bool:
        """True if the configured serial device is reachable.

        ``os.path.exists`` alone gives false positives: a stable udev symlink
        like ``/dev/parking-gate`` can survive after the USB-serial adapter
        was unplugged (briefly) or the target tty disappeared. Probe the
        kernel directly with a non-blocking ``os.open`` on the resolved path
        — if the underlying tty is gone we get ENOENT/ENXIO immediately
        without blocking on TTY hangup.
        """
        if not self.device:
            return False
        try:
            real = os.path.realpath(self.device)
        except OSError:
            return False
        if not os.path.exists(real):
            return False
        try:
            fd = os.open(real, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        except OSError:
            return False
        with contextlib.suppress(OSError):
            os.close(fd)
        return True

    async def open(self) -> bool:
        """Open boom barrier, schedule auto-close. Returns True on serial write success."""
        async with self._lock:
            return await asyncio.to_thread(self._open_sync)

    def _open_sync(self) -> bool:
        if not self._open_bytes:
            logger.error("gate_open_no_command", gate_id=self.gate_id)
            return False
        try:
            ser = serial.Serial(self.device, self.baudrate, timeout=1)
        except Exception as e:
            logger.error("gate_serial_open_failed", gate_id=self.gate_id, error=str(e))
            return False

        try:
            ser.write(self._open_bytes)
            logger.info("gate_opened", gate_id=self.gate_id, device=self.device)

            if self._close_bytes and self.close_delay_s > 0:
                time.sleep(self.close_delay_s)
                ser.write(self._close_bytes)
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
