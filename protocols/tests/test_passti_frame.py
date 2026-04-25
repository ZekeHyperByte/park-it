"""Tests for PASSTI frame protocol."""

import pytest

from protocols.passti.frame import (
    CARD_TYPES,
    STATUS_MESSAGES,
    build_frame,
    parse_response,
)


class TestBuildFrame:
    """Test frame builder."""

    def test_frame_structure(self):
        """Frame has correct structure."""
        frame = build_frame(0x02, b"\x01\x02\x03")

        assert frame[0] == 0x02  # STX
        # LEN-H, LEN-L
        assert frame[3] == 0xEF
        assert frame[4] == 0x01
        assert frame[5] == 0x02  # CMD

    def test_empty_data(self):
        """Frame with no data."""
        frame = build_frame(0x05)

        assert frame[0] == 0x02
        assert frame[5] == 0x05  # CMD

    def test_lrc_present(self):
        """Frame ends with LRC checksum."""
        frame = build_frame(0x02, b"\x01\x02\x03")
        assert len(frame) > 6


class TestParseResponse:
    """Test response parser."""

    def test_success_response(self):
        """Parse successful response."""
        # Manually construct a valid response frame
        # STX + LEN(2) + resp_code(1) + status(3) + LRC(1)
        from protocols.passti.frame import _lrc
        payload = bytes([0x00, 0x00, 0x00, 0x00])  # resp_code=00, status=00 00 00
        len_bytes = bytes([0x00, len(payload)])
        lrc = _lrc(len_bytes + payload)
        raw = bytes([0x02]) + len_bytes + payload + bytes([lrc])

        result = parse_response(raw)
        assert result["ok"] is True
        assert result["resp_code"] == 0x00
        assert result["status"] == (0x00, 0x00, 0x00)
        assert result["status_msg"] == "OK"

    def test_error_response(self):
        """Parse error response."""
        # Manually construct a valid response frame with status 01 10 04
        from protocols.passti.frame import _lrc
        payload = bytes([0x00, 0x01, 0x10, 0x04])  # resp_code=00, status=01 10 04
        len_bytes = bytes([0x00, len(payload)])
        lrc = _lrc(len_bytes + payload)
        raw = bytes([0x02]) + len_bytes + payload + bytes([lrc])

        result = parse_response(raw)
        assert result["ok"] is False
        assert result["status"] == (0x01, 0x10, 0x04)
        assert result["status_msg"] == "Insufficient balance"

    def test_too_short(self):
        """Too short response returns error."""
        result = parse_response(b"\x02\x00")
        assert result["ok"] is False
        assert "too short" in result["error"]

    def test_invalid_stx(self):
        """Invalid STX returns error."""
        result = parse_response(b"\xFF\x00\x04\xEF\x01\x00\x00\x00\x00")
        assert result["ok"] is False
        assert "STX" in result["error"]

    def test_status_messages_complete(self):
        """All expected status codes are mapped."""
        expected = {
            (0x00, 0x00, 0x00),
            (0x01, 0x10, 0x01),
            (0x01, 0x10, 0x02),
            (0x01, 0x10, 0x03),
            (0x01, 0x10, 0x04),
            (0x01, 0x10, 0x05),
            (0x01, 0x10, 0x06),
            (0x01, 0x10, 0x07),
        }
        for status in expected:
            assert status in STATUS_MESSAGES, f"Missing status {status}"

    def test_card_types_complete(self):
        """All expected card types are mapped."""
        expected = {
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
        }
        for card_type in expected:
            assert card_type in CARD_TYPES, f"Missing card type {card_type:02X}"
