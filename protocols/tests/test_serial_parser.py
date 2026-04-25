"""Tests for Serial protocol parser and transport."""

import pytest

from protocols.serial.parser import parse_rfid_card, parse_serial, _extract_wiegand
from protocols.serial.protocol import (
    SerialTransport,
    build_command,
    cmd_trig1,
    cmd_close1,
    cmd_in1on,
    cmd_in1off,
    cmd_in2on,
    cmd_in3off,
)


# ---------------------------------------------------------------------------
# Frame builder tests
# ---------------------------------------------------------------------------


def test_build_command():
    assert build_command(b"TRIG1") == b"*TRIG1#"


def test_cmd_trig1():
    assert cmd_trig1() == b"*TRIG1#"


def test_cmd_close1():
    assert cmd_close1() == b"*CLOSE1#"


def test_cmd_in1on():
    assert cmd_in1on() == b"*IN1ON#"


def test_cmd_in1off():
    assert cmd_in1off() == b"*IN1OFF#"


def test_cmd_in2on():
    assert cmd_in2on() == b"*IN2ON#"


def test_cmd_in3off():
    assert cmd_in3off() == b"*IN3OFF#"


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_parse_serial_empty():
    result = parse_serial(b"")
    assert result["in1"] is False
    assert result["in2"] is False
    assert result["in3"] is False
    assert result["in4"] is False
    assert result["wiegand_w"] is None
    assert result["wiegand_x"] is None


def test_parse_serial_in1on():
    result = parse_serial(b"*IN1ON#")
    assert result["in1"] is True
    assert result["in2"] is False
    assert result["in3"] is False


def test_parse_serial_in1off():
    result = parse_serial(b"*IN1OFF#")
    assert result["in1"] is False


def test_parse_serial_in2on():
    result = parse_serial(b"*IN2ON#")
    assert result["in2"] is True


def test_parse_serial_in3():
    result = parse_serial(b"*IN3#")
    assert result["in3"] is True


def test_parse_serial_in3off():
    result = parse_serial(b"*IN3OFF#")
    assert result["in3"] is True  # IN3OFF means vehicle passed, so in3=True


def test_parse_serial_in4on():
    result = parse_serial(b"*IN4ON#")
    assert result["in4"] is True


def test_parse_serial_multiple_inputs():
    result = parse_serial(b"*IN1ON#*IN2ON#")
    assert result["in1"] is True
    assert result["in2"] is True


# ---------------------------------------------------------------------------
# Wiegand tests
# ---------------------------------------------------------------------------


def test_extract_wiegand_w():
    assert _extract_wiegand("IN1ONWABCD", "W") == "43981"


def test_extract_wiegand_x():
    assert _extract_wiegand("IN1ONX1234", "X") == "4660"


def test_extract_wiegand_no_channel():
    assert _extract_wiegand("IN1ON", "W") is None


def test_parse_serial_wiegand_w():
    result = parse_serial(b"*WABCD#")
    assert result["wiegand_w"] == "43981"
    assert result["wiegand_x"] is None


def test_parse_serial_wiegand_x():
    result = parse_serial(b"*X1234#")
    assert result["wiegand_x"] == "4660"
    assert result["wiegand_w"] is None


def test_parse_rfid_card():
    card, card_type = parse_rfid_card(b"*WABCD#")
    assert card == "43981"
    assert card_type == "RFID"


def test_parse_uhf_card():
    card, card_type = parse_rfid_card(b"*X1234#")
    assert card == "4660"
    assert card_type == "UHF"


def test_parse_no_card():
    card, card_type = parse_rfid_card(b"*IN1ON#")
    assert card is None
    assert card_type is None


# ---------------------------------------------------------------------------
# Transport tests
# ---------------------------------------------------------------------------


def test_serial_transport_init():
    t = SerialTransport("/dev/ttyUSB0", 9600)
    assert t.port == "/dev/ttyUSB0"
    assert t.baudrate == 9600
    assert t._ser is None


def test_serial_transport_default_baudrate():
    t = SerialTransport("/dev/ttyUSB0")
    assert t.baudrate == 9600


def test_serial_transport_not_connected():
    t = SerialTransport("/dev/ttyUSB0")
    assert t.is_connected() is False
