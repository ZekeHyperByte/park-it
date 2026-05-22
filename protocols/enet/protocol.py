"""ENET gate controller protocol.

Implements the TCP-based protocol used by ENET gate controllers.
Commands are wrapped with : prefix and ; suffix.

Protocol details from v1:
- Frame: :<CMD>;
- Default port: 4000
- RFID prefix: W1 (instead of W)
- Input formats: IN1ON/IN10, IN2ON/INP21/INP21, IN3ON/IN31, IN4ON/IN41
"""

import socket


def build_command(cmd: bytes) -> bytes:
    """Wrap raw command in ENET frame.

    Args:
        cmd: Raw command bytes

    Returns:
        Framed command: : <cmd> ;
    """
    return b":" + cmd + b";"


def cmd_open1() -> bytes:
    """Open gate command."""
    return build_command(b"OPEN1")


def cmd_info() -> bytes:
    """Request controller input status."""
    return build_command(b"INFO")


def cmd_play_track(track: int) -> bytes:
    """Play MP3 track on controller.

    Args:
        track: Track number (e.g. 2, 3, 5, 6, 7, 11, 12, 13, 14)
    """
    return build_command(f"PLAYTRACK{track}".encode())


def cmd_pr4(data: bytes) -> bytes:
    """Send printer data through controller (Serial2 passthrough).

    Args:
        data: ESC/POS command bytes
    """
    return build_command(b"PR4" + data)


class EnetTransport:
    """TCP transport for ENET gate controller."""

    def __init__(self, host: str, port: int = 4000) -> None:
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None

    def connect(self, timeout: float = 5.0) -> None:
        """Establish TCP connection to controller with keepalive."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        self._sock.connect((self.host, self.port))
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        for opt, val in (
            (getattr(socket, "TCP_KEEPIDLE", None), 10),
            (getattr(socket, "TCP_KEEPINTVL", None), 5),
            (getattr(socket, "TCP_KEEPCNT", None), 3),
        ):
            if opt is not None:
                try:
                    self._sock.setsockopt(socket.IPPROTO_TCP, opt, val)
                except OSError:
                    pass

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
