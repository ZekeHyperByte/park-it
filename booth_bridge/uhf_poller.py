"""Network UHF reader polling task.

Ports legacy parking-system/uhf-reader.py into booth_bridge. Reads EPC
from a TCP-connected UHF reader, dedupes the card, calls
/api/payments/rfid/booth, and triggers a local gate open on success.
Broadcasts events to WS clients (POS) for display.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from shared.logging import get_logger

logger = get_logger("booth_uhf")

EPC_CMD = "04 FF 0F"
PRESET_VALUE = 0xFFFF
POLYNOMIAL = 0x8408


def _crc(cmd_hex: str) -> bytes:
    cmd = bytes.fromhex(cmd_hex.replace(" ", ""))
    ui = PRESET_VALUE
    for byte in cmd:
        ui ^= byte
        for _ in range(8):
            if ui & 0x0001:
                ui = (ui >> 1) ^ POLYNOMIAL
            else:
                ui >>= 1
    crc_h = (ui >> 8) & 0xFF
    crc_l = ui & 0xFF
    return cmd + bytes([crc_l, crc_h])


class UhfPoller:
    """Polls a TCP UHF reader and triggers auto-exit on member card detected."""

    def __init__(
        self,
        host: str,
        port: int,
        gate_id: str,
        gate_db_id: int,
        api_client,
        gate_opener,
        broadcast: Callable[[dict[str, Any]], Awaitable[None]],
        poll_interval_s: float = 0.5,
        dedupe_cooldown_s: float = 3.0,
    ) -> None:
        self.host = host
        self.port = port
        self.gate_id = gate_id
        self.gate_db_id = gate_db_id
        self.api = api_client
        self.opener = gate_opener
        self.broadcast = broadcast
        self.poll_interval_s = poll_interval_s
        self.dedupe_cooldown_s = dedupe_cooldown_s
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_card: str | None = None
        self._last_card_at: float = 0.0

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name=f"uhf_poll_{self.gate_id}")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    async def _run(self) -> None:
        while self._running:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
            except Exception as e:
                logger.error("uhf_connect_failed", host=self.host, port=self.port, error=str(e))
                await asyncio.sleep(3)
                continue

            logger.info("uhf_connected", host=self.host, port=self.port, gate_id=self.gate_id)

            try:
                while self._running:
                    await asyncio.sleep(self.poll_interval_s)
                    try:
                        writer.write(_crc(EPC_CMD))
                        await writer.drain()
                        raw = await asyncio.wait_for(reader.read(64), timeout=2.0)
                    except Exception as e:
                        logger.warning("uhf_read_failed", error=str(e))
                        break

                    if not raw or len(raw) < 20:
                        continue

                    hex_str = raw.hex().upper()
                    if len(hex_str) < 34:
                        continue

                    try:
                        card_number = str(int(hex_str[28:34], 16))
                    except ValueError:
                        continue

                    await self._handle_card(card_number)
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

    async def _handle_card(self, card_number: str) -> None:
        now = asyncio.get_event_loop().time()
        if card_number == self._last_card and (now - self._last_card_at) < self.dedupe_cooldown_s:
            return
        self._last_card = card_number
        self._last_card_at = now

        logger.info("uhf_card_read", card=card_number, gate_id=self.gate_id)

        result = await self.api.rfid_exit(self.gate_id, self.gate_db_id, card_number)
        success = bool(result.get("success"))

        await self.broadcast(
            {
                "event": "member_card_scanned",
                "gate_id": self.gate_id,
                "card_number": card_number,
                "success": success,
                "message": result.get("message", ""),
                "transaction_id": result.get("transaction_id"),
            }
        )

        if success:
            opened = await self.opener.open()
            if not opened:
                logger.error("uhf_open_relay_failed", card=card_number, gate_id=self.gate_id)
        else:
            logger.warning(
                "uhf_member_rejected",
                card=card_number,
                gate_id=self.gate_id,
                reason=result.get("message"),
            )
