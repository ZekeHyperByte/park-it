"""Manages serial connections to booth peripherals."""

import threading

import serial

from shared.logging import get_logger

logger = get_logger("booth_serial")


class SerialManager:
    """Manages serial connections to booth peripherals.

    One ``threading.Lock`` per peripheral guards the reset-buffer / write /
    read sequence so concurrent ``send`` calls (e.g. WS-handler emoney_deduct
    racing with a print_receipt fired by a different POS client) cannot
    interleave bytes on the same wire. Booth wiring is one port per device
    (confirmed by `_roles/booth_pc/setup.sh` defaults), so a per-peripheral
    lock is sufficient — no cross-port arbiter required.
    """

    def __init__(self, peripherals: dict) -> None:
        self.peripherals = peripherals
        self._connections: dict[str, serial.Serial] = {}
        self._locks: dict[str, threading.Lock] = {
            name: threading.Lock() for name in peripherals
        }
        self._running = False

    def _lock_for(self, peripheral: str) -> threading.Lock:
        # Late additions (peripherals not declared at construction) still get
        # a lock so the contract holds even if config grows at runtime.
        lock = self._locks.get(peripheral)
        if lock is None:
            lock = threading.Lock()
            self._locks[peripheral] = lock
        return lock

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

    def _reconnect(self, peripheral: str) -> serial.Serial:
        """Reopen a peripheral's serial port. Raises if config missing/open fails."""
        cfg = self.peripherals.get(peripheral)
        if not cfg:
            raise RuntimeError(f"No config for peripheral: {peripheral}")
        old = self._connections.pop(peripheral, None)
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        conn = serial.Serial(
            port=cfg["device"],
            baudrate=cfg.get("baudrate", 38400),
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
        )
        self._connections[peripheral] = conn
        logger.info("serial_reconnected", peripheral=peripheral, device=cfg["device"])
        return conn

    def send(self, peripheral: str, data: bytes) -> bytes:
        """Send data to a peripheral and read response.

        Reopens the port once on I/O failure (cable unplug / device reset)
        instead of failing permanently until the bridge is restarted.

        Holds the per-peripheral lock for the whole reset+write+read window
        so two callers can't garble each other's frames on the same port.
        """
        lock = self._lock_for(peripheral)
        with lock:
            conn = self._connections.get(peripheral)
            if conn is None or not conn.is_open:
                conn = self._reconnect(peripheral)
            try:
                conn.reset_input_buffer()
                conn.write(data)
                return conn.read(1024)
            except (serial.SerialException, OSError) as e:
                logger.warning("serial_send_failed_retrying", peripheral=peripheral, error=str(e))
                conn = self._reconnect(peripheral)
                conn.reset_input_buffer()
                conn.write(data)
                return conn.read(1024)

    def write_only(self, peripheral: str, data: bytes) -> int:
        """Send data without waiting for a response.

        For ESC/POS receipt printers and other devices that don't ACK: the
        ``send`` path's ``read(1024)`` would wait the full 1s timeout for
        bytes that never come. ``write_only`` skips the read entirely.

        Returns the number of bytes written. Still holds the per-peripheral
        lock so a concurrent ``send`` on the same port can't interleave.
        """
        lock = self._lock_for(peripheral)
        with lock:
            conn = self._connections.get(peripheral)
            if conn is None or not conn.is_open:
                conn = self._reconnect(peripheral)
            try:
                return int(conn.write(data) or 0)
            except (serial.SerialException, OSError) as e:
                logger.warning(
                    "serial_write_failed_retrying", peripheral=peripheral, error=str(e)
                )
                conn = self._reconnect(peripheral)
                return int(conn.write(data) or 0)

    def is_connected(self, peripheral: str) -> bool:
        """Check if a peripheral is connected."""
        conn = self._connections.get(peripheral)
        return conn is not None and conn.is_open
