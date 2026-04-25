"""Serial gate controller protocol.

Implements RS-232 serial communication for gate controllers.
Commands are wrapped with * prefix and # suffix.

Protocol details from v1:
- Frame: *<CMD>#
- Connection: Direct serial port (RS-232) via pyserial
- No built-in audio — uses external MP3 playback
- No built-in LED display controller
"""

from typing import Callable


def build_command(cmd: bytes) -> bytes:
    """Wrap raw command in Serial frame.

    Args:
        cmd: Raw command bytes

    Returns:
        Framed command: * <cmd> #
    """
    return b"*" + cmd + b"#"


def cmd_trig1() -> bytes:
    """Open gate command (trigger relay 1)."""
    return build_command(b"TRIG1")


def cmd_close1() -> bytes:
    """Close gate command."""
    return build_command(b"CLOSE1")


def cmd_in1on() -> bytes:
    """Simulated IN1 ON status (for testing)."""
    return build_command(b"IN1ON")


def cmd_in1off() -> bytes:
    """Simulated IN1 OFF status (for testing)."""
    return build_command(b"IN1OFF")


def cmd_in2on() -> bytes:
    """Simulated IN2 ON status (for testing)."""
    return build_command(b"IN2ON")


def cmd_in3off() -> bytes:
    """Simulated vehicle passed (IN3 OFF)."""
    return build_command(b"IN3OFF")


class SerialTransport:
    """Serial transport for gate controller via pyserial.

    This transport requires the `pyserial` package.
    The protocol layer itself (this file) is stdlib-only,
    but SerialTransport imports pyserial.
    """

    def __init__(self, port: str, baudrate: int = 9600) -> None:
        self.port = port
        self.baudrate = baudrate
        self._ser = None

    def connect(self, timeout: float = 1.0) -> None:
        """Open serial port connection."""
        import serial

        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=timeout,
            write_timeout=timeout,
        )

    def close(self) -> None:
        """Close serial port."""
        if self._ser:
            self._ser.close()
            self._ser = None

    def send(self, command: bytes) -> None:
        """Send command to controller."""
        if self._ser is None:
            raise RuntimeError("Not connected")
        self._ser.write(command)

    def read_until(self, terminator: bytes = b"#", size: int = 1024) -> bytes:
        """Read from serial until terminator is found.

        This is the primary read method for serial controllers,
        which send variable-length responses.
        """
        if self._ser is None:
            raise RuntimeError("Not connected")
        return self._ser.read_until(terminator, size)

    def readline(self) -> bytes:
        """Read a line from serial."""
        if self._ser is None:
            raise RuntimeError("Not connected")
        return self._ser.readline()

    def is_connected(self) -> bool:
        """Check if serial port is open."""
        if self._ser is None:
            return False
        return self._ser.is_open
