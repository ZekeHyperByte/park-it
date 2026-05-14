"""PASSTI reader transport abstraction.

Supports two connection modes:
1. ControllerPassthroughTransport - Reader connected to controller Serial2
2. DirectSerialTransport - Reader connected directly to PC via USB/Serial
"""

import time
from abc import ABC, abstractmethod
from typing import Any


class EmoneyReaderTransport(ABC):
    """Abstract transport for PASSTI e-money reader."""

    @abstractmethod
    async def send_recv(self, frame: bytes, timeout: float = 10.0) -> dict[str, Any]:
        """Send a PASSTI frame and return parsed response.

        Args:
            frame: Raw PASSTI command frame
            timeout: Seconds to wait for response

        Returns:
            Dict with at minimum:
                - ok: bool
                - resp_code: int
                - status: tuple
                - status_msg: str
                - body: bytes
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close transport connection."""
        ...


class ControllerPassthroughTransport(EmoneyReaderTransport):
    """Reader connected to controller Serial2.

    Sends commands via controller's QR5 passthrough (TCP socket).
    This matches the working prototype implementation.
    """

    def __init__(self, shared_socket: Any) -> None:
        """Initialize with a shared TCP socket to the controller.

        Args:
            shared_socket: Connected socket.socket instance
        """
        self._sock = shared_socket

    async def send_recv(self, frame: bytes, timeout: float = 10.0) -> dict[str, Any]:
        """Send frame via controller passthrough and read response.

        Uses PASSTI frame length from header instead of searching for \\xa9,
        because \\xa9 bytes can appear inside encrypted transaction log data.
        """
        import socket

        # Build controller passthrough command: \xa6 QR5 <frame> \xa9
        qr_cmd = bytes([0xA6]) + b"QR5" + frame + bytes([0xA9])

        try:
            self._sock.sendall(qr_cmd)
        except Exception as e:
            return {"ok": False, "error": f"Failed to send to controller: {e}"}

        buffer = b""
        qt_data = None
        expected_qt_len = None

        try:
            start = time.time()
            while time.time() - start < timeout + 2:
                try:
                    self._sock.settimeout(0.5)
                    chunk = self._sock.recv(4096)
                    if chunk:
                        buffer += chunk
                except socket.timeout:
                    pass

                # Find \xa6QT header
                idx = buffer.find(b"\xa6QT")
                if idx == -1:
                    continue

                # Calculate expected frame length from PASSTI header
                qt_start = idx + 3
                if expected_qt_len is None and len(buffer) >= qt_start + 3:
                    if buffer[qt_start] == 0x02:  # STX
                        payload_len = (buffer[qt_start + 1] << 8) | buffer[qt_start + 2]
                        expected_qt_len = 3 + payload_len + 1

                # Check if we have complete frame
                if expected_qt_len and len(buffer) >= qt_start + expected_qt_len:
                    qt_data = buffer[qt_start : qt_start + expected_qt_len]
                    break

        except Exception as e:
            return {"ok": False, "error": f"Communication error: {e}"}

        if qt_data is None:
            if len(buffer) == 0:
                return {"ok": False, "error": "No response from controller"}
            if b"\xa6QT" not in buffer:
                return {"ok": False, "error": "No card detected (timeout)", "status": (0x01, 0x10, 0x02)}
            return {"ok": False, "error": "Incomplete QT response"}

        # Parse the PASSTI response from qt_data
        from protocols.passti.frame import parse_response

        return parse_response(qt_data)

    async def close(self) -> None:
        """No-op — socket is managed by the gate controller."""
        pass


class DirectSerialTransport(EmoneyReaderTransport):
    """Reader connected directly to PC via USB-to-Serial or RS-232.

    Uses pyserial for direct serial communication.
    """

    def __init__(self, port: str, baudrate: int = 38400) -> None:
        """Initialize with serial port settings.

        Args:
            port: Serial port path (e.g. '/dev/ttyUSB0' or 'COM3')
            baudrate: Baud rate (default 38400 for PASSTI)
        """
        self._port = port
        self._baudrate = baudrate
        self._serial = None

    async def send_recv(self, frame: bytes, timeout: float = 10.0) -> dict[str, Any]:
        """Send frame via direct serial and read response."""
        import serial

        if self._serial is None:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=timeout,
            )

        from protocols.passti.frame import parse_response

        try:
            self._serial.write(frame)
            # Read STX + LEN-H + LEN-L first to determine exact frame length.
            # Do NOT use read_until(LRC) — the response LRC differs from the
            # command LRC, and its value can appear inside encrypted card log data.
            header = self._serial.read(3)
            if len(header) < 3:
                return {"ok": False, "error": "Serial timeout reading response header"}
            if header[0] != 0x02:  # STX
                return {"ok": False, "error": f"Bad response STX: {header[0]:#04x}"}
            data_len = (header[1] << 8) | header[2]
            rest = self._serial.read(data_len + 1)  # payload + LRC
            if len(rest) < data_len + 1:
                return {"ok": False, "error": "Serial timeout reading response payload"}
            raw = header + rest
        except Exception as e:
            return {"ok": False, "error": f"Serial communication error: {e}"}

        return parse_response(raw)

    async def close(self) -> None:
        """Close serial port."""
        if self._serial:
            self._serial.close()
            self._serial = None
