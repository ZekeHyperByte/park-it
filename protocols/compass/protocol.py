"""Compass gate controller protocol.

Implements the TCP-based protocol used by Compass gate controllers.
Commands are wrapped with \xa6 prefix and \xa9 suffix.
"""

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
    """Open gate command (trigger relay 1)."""
    return build_command(b"TRIG1")


def cmd_trig2() -> bytes:
    """Close gate command (trigger relay 2) — for DUAL relay mode."""
    return build_command(b"TRIG2")


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

    def is_connected(self) -> bool:
        """Check if socket is connected."""
        if self._sock is None:
            return False
        try:
            self._sock.getpeername()
            return True
        except Exception:
            return False
