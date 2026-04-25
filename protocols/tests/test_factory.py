"""Tests for protocol factory."""

import pytest

from protocols.factory import create_transport, create_parser


def test_create_transport_compass():
    transport = create_transport("compass", host="192.168.1.100", port=5000)
    assert transport.host == "192.168.1.100"
    assert transport.port == 5000


def test_create_transport_compass_default_port():
    transport = create_transport("compass", host="192.168.1.100")
    assert transport.port == 5000


def test_create_transport_enet():
    transport = create_transport("enet", host="192.168.1.100", port=4000)
    assert transport.host == "192.168.1.100"
    assert transport.port == 4000


def test_create_transport_enet_default_port():
    transport = create_transport("enet", host="192.168.1.100")
    assert transport.port == 4000


def test_create_transport_serial():
    transport = create_transport("serial", port="/dev/ttyUSB0", baudrate=115200)
    assert transport.port == "/dev/ttyUSB0"
    assert transport.baudrate == 115200


def test_create_transport_serial_default_baudrate():
    transport = create_transport("serial", port="/dev/ttyUSB0")
    assert transport.baudrate == 9600


def test_create_transport_unknown():
    with pytest.raises(ValueError, match="Unknown protocol"):
        create_transport("unknown")


def test_create_transport_case_insensitive():
    transport = create_transport("COMPASS", host="192.168.1.100")
    assert transport.port == 5000


# Parser factory tests


def test_create_parser_compass():
    parser = create_parser("compass")
    from protocols.compass.parser import parse_stat

    assert parser is parse_stat


def test_create_parser_enet():
    parser = create_parser("enet")
    from protocols.enet.parser import parse_info

    assert parser is parse_info


def test_create_parser_serial():
    parser = create_parser("serial")
    from protocols.serial.parser import parse_serial

    assert parser is parse_serial


def test_create_parser_unknown():
    with pytest.raises(ValueError, match="Unknown protocol"):
        create_parser("unknown")
