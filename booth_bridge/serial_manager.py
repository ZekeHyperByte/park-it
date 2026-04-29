"""Manages serial connections to booth peripherals."""

import asyncio

import serial

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
