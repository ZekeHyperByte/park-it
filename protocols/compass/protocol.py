"""Compass gate controller protocol.

Implements the TCP-based protocol used by Compass gate controllers.
Commands are wrapped with \xa6 prefix and \xa9 suffix.
"""

import asyncio
import socket
from typing import Callable


def build_command(cmd: bytes) -> bytes:
    """Wrap raw command in Compass frame.

    Args:
        cmd: Raw command bytes

    Returns:
        Framed command: \xa6 <cmd> \xa9
    """
    return bytes([0xA6]) + cmd + bytes([0xA9])


def cmd_trig1() -> bytes:
    """Pulse relay 1 for 1s — SINGLE relay mode open."""
    return build_command(b"TRIG1")


def cmd_trig2() -> bytes:
    """Pulse relay 2 for 1s."""
    return build_command(b"TRIG2")


def cmd_open1() -> bytes:
    """Open gate with interlocking: relay2 off, relay3 off, relay1 on 1s — DUAL/TRIPLE."""
    return build_command(b"OPEN1")


def cmd_close1() -> bytes:
    """Close gate with interlocking: relay1 off, relay3 off, relay2 on 1s — DUAL/TRIPLE."""
    return build_command(b"CLOSE1")


def cmd_stop1() -> bytes:
    """Brake gate motor: relay1 off, relay2 off, relay3 on 1s — TRIPLE only."""
    return build_command(b"STOP1")


def cmd_stat() -> bytes:
    """Request controller status."""
    return build_command(b"STAT")


def cmd_mt(track: str) -> bytes:
    """Play MP3 track on controller.

    Args:
        track: Track number string (e.g. '00007')
    """
    return build_command(f"MT{track}".encode())


def cmd_ds(line1: str, line2: str = "") -> bytes:
    """Show two-line text on controller LED display.

    Args:
        line1: First line text
        line2: Second line text
    """
    text = line1.encode() + b"|" + line2.encode()
    return build_command(b"DSD913003" + text)


def cmd_dsu() -> bytes:
    """Reset controller LED display."""
    return build_command(b"DSU")


def cmd_rss(
    interval_100ms: int = 2,
    *,
    in1_on: bool = True,
    in1_off: bool = True,
    in2_on: bool = True,
    in2_off: bool = False,
    in3_on: bool = True,
    in3_off: bool = True,
    in4_on: bool = True,
    in4_off: bool = False,
    play_end: bool = False,
    no_track: bool = False,
    wiegand: bool = True,
) -> bytes:
    """Configure RSS push mode — controller auto-pushes input events.

    Args:
        interval_100ms: Resend interval in units of 100ms (1–99). Default 2 = 200ms.
        in1_on/off ... wiegand: Enable push for each event type.
    """
    flags = "".join([
        "1" if in1_on else "0",
        "1" if in1_off else "0",
        "1" if in2_on else "0",
        "1" if in2_off else "0",
        "1" if in3_on else "0",
        "1" if in3_off else "0",
        "1" if in4_on else "0",
        "1" if in4_off else "0",
        "1" if play_end else "0",
        "1" if no_track else "0",
        "1" if wiegand else "0",
    ])
    return build_command(f"RSS{interval_100ms:02d}{flags}".encode())


# RSS acknowledgement commands — stop repeated resend for each event type
def cmd_ack_in1on() -> bytes:
    return build_command(b"IN1ONOK")

def cmd_ack_in1off() -> bytes:
    return build_command(b"IN1OFFOK")

def cmd_ack_in2on() -> bytes:
    return build_command(b"IN2ONOK")

def cmd_ack_in2off() -> bytes:
    return build_command(b"IN2OFFOK")

def cmd_ack_in3on() -> bytes:
    return build_command(b"IN3ONOK")

def cmd_ack_in3off() -> bytes:
    return build_command(b"IN3OFFOK")

def cmd_ack_in4on() -> bytes:
    return build_command(b"IN4ONOK")

def cmd_ack_in4off() -> bytes:
    return build_command(b"IN4OFFOK")

def cmd_ack_wiegand() -> bytes:
    return build_command(b"WOK")


def cmd_pr3(data: bytes) -> bytes:
    """Send data to serial port 1 at 9600 baud (standard printer baud rate)."""
    return build_command(b"PR3" + data)


def cmd_qr5(frame: bytes) -> bytes:
    """Send data to Serial2 (PASSTI reader passthrough).

    Args:
        frame: PASSTI command frame
    """
    return build_command(b"QR5" + frame)


class CompassTransport:
    """TCP transport for Compass gate controller."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None

    def connect(self, timeout: float = 5.0) -> None:
        """Establish TCP connection to controller."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        self._sock.connect((self.host, self.port))

    def close(self) -> None:
        """Close TCP connection."""
        if self._sock:
            self._sock.close()
            self._sock = None

    def send(self, command: bytes) -> None:
        """Send command to controller."""
        if self._sock is None:
            raise RuntimeError("Not connected")
        self._sock.sendall(command)

    def send_recv(self, command: bytes, timeout: float = 1.0) -> bytes:
        """Send command and read response."""
        if self._sock is None:
            raise RuntimeError("Not connected")
        self._sock.settimeout(timeout)
        self._sock.sendall(command)
        try:
            return self._sock.recv(1024)
        except socket.timeout:
            return b""

    async def recv_async(self, timeout: float = 0.5) -> bytes:
        """Async recv via executor — doesn't block event loop.

        Used by RSS listener to receive pushed events without STAT polling.
        Reads are lock-free (TCP full-duplex); only writes need the caller's lock.
        """
        if self._sock is None:
            return b""
        self._sock.settimeout(timeout)
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, self._sock.recv, 1024)
        except socket.timeout:
            return b""
        except OSError:
            return b""

    def is_connected(self) -> bool:
        """Check if socket is connected."""
        if self._sock is None:
            return False
        try:
            self._sock.getpeername()
            return True
        except Exception:
            return False


class SerialTransport:
    """RS232/USB serial transport for barrier gate controllers (e.g. Interface Barrier Gate v1.0).

    Mirrors CompassTransport interface so daemons can use either transport
    interchangeably. Same Compass framing protocol (\xa6...\xa9) over serial.
    PASSTI passthrough is NOT supported — serial controllers lack the QR5 tunnel.
    """

    def __init__(self, device: str, baudrate: int = 9600) -> None:
        self.device = device
        self.baudrate = baudrate
        self._ser: "serial.Serial | None" = None

    def connect(self, timeout: float = 5.0) -> None:
        import serial as _serial
        self._ser = _serial.Serial(
            port=self.device,
            baudrate=self.baudrate,
            bytesize=_serial.EIGHTBITS,
            parity=_serial.PARITY_NONE,
            stopbits=_serial.STOPBITS_ONE,
            timeout=timeout,
        )

    def close(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._ser = None

    def send(self, command: bytes) -> None:
        if self._ser is None or not self._ser.is_open:
            raise RuntimeError("Not connected")
        self._ser.write(command)

    def send_recv(self, command: bytes, timeout: float = 1.0) -> bytes:
        if self._ser is None or not self._ser.is_open:
            raise RuntimeError("Not connected")
        self._ser.timeout = timeout
        self._ser.write(command)
        return self._ser.read(1024)

    async def recv_async(self, timeout: float = 0.5) -> bytes:
        if self._ser is None or not self._ser.is_open:
            return b""
        self._ser.timeout = timeout
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, self._ser.read, 1024)
        except Exception:
            return b""

    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open
