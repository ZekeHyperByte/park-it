"""Tests for settlement file generation per Multibank v1.3 §I."""

import pytest
from datetime import datetime

from workers.background.settlement_file import (
    build_settlement_content,
    generate_filename,
)


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
                {"settlement_payload_hex": "0102"},
                {"settlement_payload_hex": "0304"},
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
            transactions=[{"settlement_payload_hex": "AABBCC"}],
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

    def test_uppercase_payload(self):
        """Settlement files use uppercase hex per Multibank examples."""
        content = build_settlement_content(
            transactions=[{"settlement_payload_hex": "abcdef"}],
            total_amount=10,
        )
        assert "ABCDEF" in content
        assert "abcdef" not in content

    def test_appendix_vector_v1_12(self):
        """Match the V1.12 §IV.3 'Deduct Rp. 1' appendix vector exactly.

        The deduct response body (cardtype through CardLog) for that vector is
        the multi-line hex below. Per Multibank v1.3 §I, this body is what
        appears verbatim in the settlement file — no STX/LEN/RespCode/Status/
        LRC bytes around it.
        """
        body_hex = (
            "01"  # cardtype = Luminos
            "02034567890ABCDE"  # MID (8 bytes)
            "87654321"  # TID (4 bytes)
            "10122017121550"  # DateTime BCD ddmmyyyyhhnnss
            "5710120620170005"  # Card No (8 bytes)
            "00000001"  # Deduct amount = Rp 1
            "0001D0CC"  # Remaining balance
            "00000001"  # Trans counter
            # CardLog (variable length) — verbatim from V1.12 §IV.3
            "CDDDF8D374178432ECDC02FA9E616476DC7D3341B24FCDA12352546FF45B5ADA79F23"
            "87FB6800990EBDAD1EDBCDD3CBA5998E7A746048523759750178AE62DA5355C9CB17"
            "AF5F34DFF35865FAF960AF4194C5F2B622CCABC9BB09538B076B7F56344ACC65BC7B9B4"
        )
        content = build_settlement_content(
            transactions=[{"settlement_payload_hex": body_hex}],
            total_amount=1,
        )
        lines = content.split("\n")
        assert lines[0] == "001" + "0000000001"
        assert lines[1] == body_hex
        # Critical: the line must NOT start with the PASSTI STX byte 02 nor
        # the response code byte 00 — otherwise the bank rejects with
        # status 01 (Invalid Format) or 07 (Data Corrupt).
        assert not lines[1].startswith("02")
        assert lines[1].startswith("01")  # cardtype byte

    def test_rejects_oversize_batch(self):
        """Multibank v1.3: max 999 transactions per file."""
        with pytest.raises(ValueError, match="999 transactions"):
            build_settlement_content(
                transactions=[{"settlement_payload_hex": "00"}] * 1000,
                total_amount=0,
            )

    def test_rejects_oversize_amount(self):
        """Total amount field is 10 digits."""
        with pytest.raises(ValueError, match="out of range"):
            build_settlement_content(
                transactions=[{"settlement_payload_hex": "00"}],
                total_amount=10_000_000_000,
            )
