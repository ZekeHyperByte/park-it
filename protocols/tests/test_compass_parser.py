"""Tests for Compass controller parser."""


from protocols.compass.parser import parse_rfid_card, parse_stat


class TestParseStat:
    """Test STAT response parser."""

    def test_empty_response(self):
        """Empty response has no inputs."""
        result = parse_stat(b"")
        assert result["in1"] is False
        assert result["in2"] is False
        assert result["in3"] is False
        assert result["in4"] is False
        assert result["wiegand_w"] is None
        assert result["wiegand_x"] is None

    def test_in2_on(self):
        """Detect IN2 ON."""
        result = parse_stat(b"\xa6STATIN2ON\xa9")
        assert result["in2"] is True
        assert result["in1"] is False

    def test_in1_on(self):
        """Detect IN1 ON."""
        result = parse_stat(b"\xa6STATIN1ON\xa9")
        assert result["in1"] is True

    def test_wiegand_w(self):
        """Parse Wiegand W (RFID) card."""
        # Card hex = 1234 -> decimal = 4660
        result = parse_stat(b"\xa6STATW1234\xa9")
        assert result["wiegand_w"] == "4660"
        assert result["wiegand_x"] is None

    def test_wiegand_x(self):
        """Parse Wiegand X (UHF) card."""
        result = parse_stat(b"\xa6STATXABCD\xa9")
        assert result["wiegand_x"] == "43981"
        assert result["wiegand_w"] is None

    def test_multiple_inputs(self):
        """Multiple inputs active."""
        result = parse_stat(b"\xa6STATIN2ONIN4ONW1234\xa9")
        assert result["in2"] is True
        assert result["in4"] is True
        assert result["wiegand_w"] == "4660"

    def test_stat1_format(self):
        """STAT1 format for IN2."""
        result = parse_stat(b"\xa6STAT1\xa9")
        assert result["in2"] is True

    def test_stat10_format(self):
        """STAT10 format for IN1."""
        result = parse_stat(b"\xa6STAT10\xa9")
        assert result["in1"] is True


class TestParseRfidCard:
    """Test RFID card parser."""

    def test_no_card(self):
        """No card in response."""
        card, card_type = parse_rfid_card(b"\xa6STAT\xa9")
        assert card is None
        assert card_type is None

    def test_rfid_card(self):
        """RFID card detected."""
        card, card_type = parse_rfid_card(b"\xa6STATW1234\xa9")
        assert card == "4660"
        assert card_type == "RFID"

    def test_uhf_card(self):
        """UHF card detected."""
        card, card_type = parse_rfid_card(b"\xa6STATXABCD\xa9")
        assert card == "43981"
        assert card_type == "UHF"

    def test_rfid_priority(self):
        """RFID takes priority over UHF if both present."""
        card, card_type = parse_rfid_card(b"\xa6STATW1234XABCD\xa9")
        assert card == "4660"
        assert card_type == "RFID"
