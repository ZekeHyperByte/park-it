"""Tests for ENET protocol parser and transport."""

import pytest

from protocols.enet.parser import parse_info, parse_rfid_card, _extract_wiegand_w1
from protocols.enet.protocol import (
    EnetTransport,
    build_command,
    cmd_info,
    cmd_open1,
    cmd_play_track,
    cmd_pr4,
)


# ---------------------------------------------------------------------------
# Frame builder tests
# ---------------------------------------------------------------------------


def test_build_command():
    assert build_command(b"OPEN1") == b":OPEN1;"


def test_cmd_open1():
    assert cmd_open1() == b":OPEN1;"


def test_cmd_info():
    assert cmd_info() == b":INFO;"


def test_cmd_play_track():
    assert cmd_play_track(7) == b":PLAYTRACK7;"
    assert cmd_play_track(2) == b":PLAYTRACK2;"


def test_cmd_pr4():
    assert cmd_pr4(b"\x1b\x40") == b":PR4\x1b\x40;"


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_parse_info_empty():
    result = parse_info(b"")
    assert result["in1"] is False
    assert result["in2"] is False
    assert result["in3"] is False
    assert result["in4"] is False
    assert result["wiegand_w"] is None


def test_parse_info_in1on():
    result = parse_info(b":IN1ON;")
    assert result["in1"] is True
    assert result["in2"] is False


def test_parse_info_inp11():
    result = parse_info(b":INP11;")
    assert result["in1"] is True


def test_parse_info_stat10():
    result = parse_info(b":STAT10;")
    assert result["in1"] is True


def test_parse_info_in2on():
    result = parse_info(b":IN2ON;")
    assert result["in2"] is True


def test_parse_info_inp21():
    result = parse_info(b":INP21;")
    assert result["in2"] is True


def test_parse_info_in3on():
    result = parse_info(b":IN3ON;")
    assert result["in3"] is True


def test_parse_info_in31():
    result = parse_info(b":IN31;")
    assert result["in3"] is True


def test_parse_info_in4on():
    result = parse_info(b":IN4ON;")
    assert result["in4"] is True


def test_parse_info_in41():
    result = parse_info(b":IN41;")
    assert result["in4"] is True


def test_parse_info_multiple_inputs():
    result = parse_info(b":IN1ON;IN2ON;")
    assert result["in1"] is True
    assert result["in2"] is True
    assert result["in3"] is False
    assert result["in4"] is False


# ---------------------------------------------------------------------------
# Wiegand W1 tests
# ---------------------------------------------------------------------------


def test_extract_wiegand_w1_simple():
    assert _extract_wiegand_w1("W1ABCD;") == "43981"


def test_extract_wiegand_w1_no_prefix():
    assert _extract_wiegand_w1("ABCD;") is None


def test_extract_wiegand_w1_empty():
    assert _extract_wiegand_w1("W1;") is None


def test_parse_info_wiegand_w1():
    result = parse_info(b":W1ABCD;")
    assert result["wiegand_w"] == "43981"


def test_parse_rfid_card():
    card, card_type = parse_rfid_card(b":W1ABCD;")
    assert card == "43981"
    assert card_type == "RFID"


def test_parse_rfid_card_none():
    card, card_type = parse_rfid_card(b":IN1ON;")
    assert card is None
    assert card_type is None


# ---------------------------------------------------------------------------
# Transport tests
# ---------------------------------------------------------------------------


def test_enet_transport_init():
    t = EnetTransport("192.168.1.100", 4000)
    assert t.host == "192.168.1.100"
    assert t.port == 4000
    assert t._sock is None


def test_enet_transport_default_port():
    t = EnetTransport("192.168.1.100")
    assert t.port == 4000


def test_enet_transport_not_connected():
    t = EnetTransport("192.168.1.100")
    assert t.is_connected() is False
