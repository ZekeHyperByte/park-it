"""TCP hardware simulator for gate controller testing.

Simulates Compass protocol controller board:
- Accepts commands: STAT, TRIG1, OPEN1, MTxxxxx, DS..., PR3..., PR4...
- Can simulate inputs: IN1 ON/OFF, IN2 ON, IN3 ON/OFF, IN4 ON
- Can simulate Wiegand reads: W<hex>, X<hex> (UHF)
"""

import asyncio
import logging

logger = logging.getLogger("controller_sim")


class CompassControllerSimulator:
    """Compass protocol TCP simulator."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.server: asyncio.Server | None = None
        self._in1 = False
        self._in2 = False
        self._in3 = False
        self._in4 = False
        self._wiegand_data: str | None = None
        self._command_log: list[bytes] = []

    async def start(self) -> None:
        self.server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        self.port = self.server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
        logger.info("controller_sim_started", host=self.host, port=self.port)

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("controller_sim_stopped")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        addr = writer.get_extra_info("peername")
        logger.info("controller_sim_client_connected", addr=addr)
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                self._command_log.append(data)
                response = self._process_command(data)
                if response:
                    writer.write(response)
                    await writer.drain()
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info("controller_sim_client_disconnected", addr=addr)

    def _process_command(self, data: bytes) -> bytes | None:
        """Process incoming command and return response."""
        # Compass frame: \xa6 ... \xa9
        if not (data.startswith(b"\xa6") and data.endswith(b"\xa9")):
            return None

        inner = data[1:-1].decode("ascii", errors="ignore")

        if inner == "STAT":
            return self._build_stat_response()
        elif inner == "TRIG1":
            logger.info("controller_sim_trig1")
            return b"\xa6OK\xa9"
        elif inner == "OPEN1":
            logger.info("controller_sim_open1")
            return b"\xa6OK\xa9"
        elif inner.startswith("MT"):
            logger.info("controller_sim_audio", track=inner[2:])
            return b"\xa6OK\xa9"
        elif inner.startswith("DS") or inner.startswith("U"):
            logger.info("controller_sim_display", text=inner)
            return b"\xa6OK\xa9"
        elif inner.startswith("PR"):
            logger.info("controller_sim_print", cmd=inner[:3])
            return b"\xa6OK\xa9"

        return b"\xa6OK\xa9"

    def _build_stat_response(self) -> bytes:
        """Build STAT response with current input states."""
        parts = []
        if self._in1:
            parts.append("IN1ON")
        else:
            parts.append("IN1OFF")
        if self._in2:
            parts.append("IN2ON")
        if self._in3:
            parts.append("IN3ON")
        if self._in4:
            parts.append("IN4ON")
        if self._wiegand_data:
            parts.append(self._wiegand_data)
            self._wiegand_data = None  # Clear after read

        response = "|".join(parts) if parts else "IN1OFF"
        return b"\xa6" + response.encode("ascii") + b"\xa9"

    # Simulation controls
    def set_in1(self, value: bool) -> None:
        self._in1 = value

    def set_in2(self, value: bool) -> None:
        self._in2 = value

    def set_in3(self, value: bool) -> None:
        self._in3 = value

    def set_in4(self, value: bool) -> None:
        self._in4 = value

    def inject_wiegand(self, card_hex: str, channel: str = "W") -> None:
        self._wiegand_data = f"{channel}{card_hex}"

    def get_command_log(self) -> list[bytes]:
        return self._command_log.copy()

    def clear_command_log(self) -> None:
        self._command_log.clear()
