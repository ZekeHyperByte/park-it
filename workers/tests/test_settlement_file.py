import pytest
from datetime import datetime

from workers.background.settlement_file import generate_filename, build_settlement_content


class TestGenerateFilename:
    def test_filename_format(self):
        dt = datetime(2026, 4, 26, 23, 55, 0)
        result = generate_filename(
            settlement_datetime=dt,
            mid="2034567890ABCDE",
            tid="87654321",
            batch_number=1,
        )
        assert result == "2026042623550002034567890ABCDE8765432101001.txt"

    def test_batch_number_padding(self):
        dt = datetime(2026, 4, 26, 23, 55, 0)
        result = generate_filename(
            settlement_datetime=dt,
            mid="2034567890ABCDE",
            tid="87654321",
            batch_number=42,
        )
        assert result == "2026042623550002034567890ABCDE8765432101042.txt"

    def test_mid_left_padding(self):
        dt = datetime(2026, 4, 26, 23, 55, 0)
        result = generate_filename(
            settlement_datetime=dt,
            mid="123",
            tid="456",
            batch_number=1,
        )
        assert result == "2026042623550000000000000001230000045601001.txt"


class TestBuildSettlementContent:
    def test_header_format(self):
        content = build_settlement_content(
            transactions=[
                {"raw_response_hex": "0102"},
                {"raw_response_hex": "0304"},
            ],
            total_amount=2500,
        )
        lines = content.split("\n")
        assert lines[0] == "0020000002500"
        assert lines[1] == "0102"
        assert lines[2] == "0304"
        assert lines[3] == ""

    def test_single_transaction(self):
        content = build_settlement_content(
            transactions=[{"raw_response_hex": "AABBCC"}],
            total_amount=500,
        )
        lines = content.split("\n")
        assert lines[0] == "0010000000500"
        assert lines[1] == "AABBCC"

    def test_empty_transactions(self):
        content = build_settlement_content(
            transactions=[],
            total_amount=0,
        )
        lines = content.split("\n")
        assert lines[0] == "0000000000000"
