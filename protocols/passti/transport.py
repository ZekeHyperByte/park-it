"""PASSTI reader transport abstraction.

Supports two connection modes:
1. ControllerPassthroughTransport - Reader connected to controller Serial2
2. DirectSerialTransport - Reader connected directly to PC via USB/Serial
"""

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
        """Send frame via controller passthrough and read response."""
        import socket

        # Build controller passthrough command: \xa6 QR5 <frame> \xa9
        qr_cmd = bytes([0xA6]) + b"QR5" + frame + bytes([0xA9])

        try:
            self._sock.sendall(qr_cmd)
        except Exception as e:
            return {"ok": False, "error": f"Failed to send to controller: {e}"}

        buffer = b""
        qt_data = None

        try:
            self._sock.settimeout(timeout + 2)

            while True:
                try:
                    chunk = self._sock.recv(2048)
                    if not chunk:
                        break
                    buffer += chunk
                except socket.timeout:
                    break

                # Scan for QT response
                idx = buffer.find(b"\xa6QT")
                if idx != -1:
                    footer_idx = buffer.find(b"\xa9", idx + 3)
                    if footer_idx != -1:
                        qt_data = buffer[idx + 3 : footer_idx]
                        break

                # Also accept plain QT response
                idx = buffer.find(b"QT")
                if idx != -1 and (idx == 0 or buffer[idx - 1 : idx] != b"\xa6"):
                    end_idx = buffer.find(b"\xa6", idx + 2)
                    if end_idx == -1:
                        end_idx = len(buffer)
                    qt_data = buffer[idx + 2 : end_idx]
                    break

        except Exception as e:
            return {"ok": False, "error": f"Communication error: {e}"}

        if qt_data is None:
            return {"ok": False, "error": "No QT response from controller serial2"}

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

        try:
            self._serial.write(frame)
            # Read response — PASSTI frame structure allows us to know when complete
            raw = self._serial.read_until(expected=bytes([frame[-1]]))
        except Exception as e:
            return {"ok": False, "error": f"Serial communication error: {e}"}

        from protocols.passti.frame import parse_response

        return parse_response(raw)

    async def close(self) -> None:
        """Close serial port."""
        if self._serial:
            self._serial.close()
            self._serial = None
