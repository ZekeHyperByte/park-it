"""Protocol factory for gate controller transports.

Provides a unified interface to instantiate the correct transport
based on gate configuration. All transports implement the same
basic interface: connect(), close(), send(), is_connected().
"""

from __future__ import annotations

from typing import Any

from shared.logging import get_logger

logger = get_logger("protocol_factory")


def create_transport(
    protocol: str,
    **kwargs: Any,
) -> Any:
    """Create a gate controller transport based on protocol type.

    Args:
        protocol: One of "compass", "enet", "serial"
        **kwargs: Protocol-specific arguments:
            - compass: host (str), port (int, default 5000)
            - enet: host (str), port (int, default 4000)
            - serial: port (str), baudrate (int, default 9600)

    Returns:
        Transport instance with connect/close/send/is_connected methods.

    Raises:
        ValueError: If protocol is unknown.
    """
    protocol = protocol.lower().strip()

    if protocol == "compass":
        from protocols.compass.protocol import CompassTransport

        host = kwargs["host"]
        port = kwargs.get("port", 5000)
        return CompassTransport(host, port)

    elif protocol == "enet":
        from protocols.enet.protocol import EnetTransport

        host = kwargs["host"]
        port = kwargs.get("port", 4000)
        return EnetTransport(host, port)

    elif protocol == "serial":
        from protocols.serial.protocol import SerialTransport

        port = kwargs["port"]
        baudrate = kwargs.get("baudrate", 9600)
        return SerialTransport(port, baudrate)

    else:
        raise ValueError(f"Unknown protocol: {protocol!r}. Supported: compass, enet, serial")


def create_parser(protocol: str):
    """Create a parser function for the given protocol.

    Args:
        protocol: One of "compass", "enet", "serial"

    Returns:
        Parser function that takes bytes and returns a dict.
    """
    protocol = protocol.lower().strip()

    if protocol == "compass":
        from protocols.compass.parser import parse_stat

        return parse_stat

    elif protocol == "enet":
        from protocols.enet.parser import parse_info

        return parse_info

    elif protocol == "serial":
        from protocols.serial.parser import parse_serial

        return parse_serial

    else:
        raise ValueError(f"Unknown protocol: {protocol!r}. Supported: compass, enet, serial")
