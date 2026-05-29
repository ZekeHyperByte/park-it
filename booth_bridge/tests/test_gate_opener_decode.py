"""Tests for GateOpener command decoding.

Covers ASCII relay commands (``*TRIG1#``, ``O1N``), hex relay commands
(``FF 01 05 ...``), and edge cases that should surface a warning so a
field tech can spot config typos in the boot log.
"""

from __future__ import annotations

from booth_bridge.gate_opener import GateOpener


def _decode(value: str) -> tuple[bytes, str, str | None]:
    return GateOpener._decode_command(value)


def test_empty_value_is_empty_mode() -> None:
    assert _decode("") == (b"", "empty", None)


def test_ascii_relay_star_trig() -> None:
    raw, mode, warn = _decode("*TRIG1#")
    assert raw == b"*TRIG1#"
    assert mode == "ascii"
    assert warn is None


def test_ascii_relay_o1n() -> None:
    raw, mode, warn = _decode("O1N")
    assert raw == b"O1N"
    assert mode == "ascii"
    assert warn is None


def test_hex_pure_lowercase() -> None:
    raw, mode, warn = _decode("ff0105")
    assert raw == bytes.fromhex("ff0105")
    assert mode == "hex"
    assert warn is None


def test_hex_with_spaces() -> None:
    raw, mode, warn = _decode("FF 01 05 00")
    assert raw == bytes.fromhex("ff010500")
    assert mode == "hex"
    assert warn is None


def test_hex_with_escaped_prefix() -> None:
    # legacy seeders sometimes used "\\xFF\\x01" style escapes.
    raw, mode, _ = _decode("\\xFF\\x01\\x05")
    assert raw == bytes.fromhex("ff0105")
    assert mode == "hex"


def test_odd_length_hex_warns() -> None:
    raw, mode, warn = _decode("ff010")
    # Falls back to ASCII but flags suspicion.
    assert raw == b"ff010"
    assert mode == "ascii"
    assert warn is not None
    assert "odd" in warn.lower()


def test_mixed_chars_for_known_ascii_relay_does_not_warn() -> None:
    # "*TRIG1#" mixes letters/digits/punctuation; we must not nag operators
    # using legitimate ASCII relays.
    _, _, warn = _decode("*TRIG2#")
    assert warn is None


def test_mixed_chars_outside_ascii_relay_warns() -> None:
    raw, mode, warn = _decode("zz12pq")
    assert mode == "ascii"
    assert raw == b"zz12pq"
    assert warn is not None
