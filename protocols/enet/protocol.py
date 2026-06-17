"""ENET gate controller protocol.

Implements the TCP-based protocol used by ENET gate controllers.
Commands are wrapped with : prefix and ; suffix.

Protocol details from v1:
- Frame: :<CMD>;
- Default port: 4000
- RFID prefix: W1 (instead of W)
- Input formats: IN1ON/IN10, IN2ON/INP21/INP21, IN3ON/IN31, IN4ON/IN41
"""

from protocols.compass.protocol import CompassTransport as EnetTransport  # noqa: F401 — ponytail: shared TCP transport


def build_command(cmd: bytes) -> bytes:
    """Wrap raw command in ENET frame."""
    return b":" + cmd + b";"


def cmd_pr4(data: bytes) -> bytes:
    """Send printer data through controller (Serial2 passthrough)."""
    return build_command(b"PR4" + data)
