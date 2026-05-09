"""Tests for settlement_uploader (Multibank v1.3 §I + §II).

Covers:
- parse_ok_response / parse_nok_response — pure parser tests against the
  V1.3 §II "Structure Response File settlement" example.
- upload_settlement_file — atomic .partial→rename pattern with a fake SFTP.

The shape of parse_ok_response changed as part of fix C1+H2: it now returns
a dict (with header fields and a results list) rather than a flat list.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from workers.background import settlement_uploader
from workers.background.settlement_uploader import (
    RESPONSE_STATUS_CODES,
    parse_nok_response,
    parse_ok_response,
    upload_settlement_file,
)


class TestParseResponse:
    def test_v1_3_appendix_example(self):
        """Match the v1.3 §II "Structure Response File settlement" example."""
        body_payload = (
            "0102034567890ABCDE87654321"
            "10122017121550"
            "5710120620170005"
            "0000000100D0CC"
            "00000001"
        )
        content = (
            "01002\n"  # header: trx_type=01, count=002
            f"{body_payload}00\n"
            f"{body_payload}02\n"
        )
        parsed = parse_ok_response(content)
        assert parsed["trx_type"] == "01"
        assert parsed["trx_count"] == 2
        assert len(parsed["results"]) == 2
        assert parsed["results"][0]["status"] == "00"
        assert parsed["results"][0]["status_description"] == "Accepted"
        assert parsed["results"][1]["status"] == "02"
        assert parsed["results"][1]["status_description"] == "Duplicate Data"
        # Payload must be the body without the 2-byte status suffix.
        assert parsed["results"][0]["settlement_payload_hex"] == body_payload.upper()

    def test_empty(self):
        assert parse_ok_response("") == {"trx_type": "", "trx_count": 0, "results": []}

    def test_status_codes_complete(self):
        for code in ("00", "01", "02", "03", "04", "05", "07", "08", "09", "10", "11"):
            assert code in RESPONSE_STATUS_CODES

    def test_unknown_status_code(self):
        content = "01001\nABCD99\n"
        parsed = parse_ok_response(content)
        assert parsed["results"][0]["status"] == "99"
        assert parsed["results"][0]["status_description"] == "Unknown"

    def test_nok_alias(self):
        """parse_nok_response uses the same format as parse_ok_response."""
        content = "01001\nABCD05\n"
        assert parse_nok_response(content) == parse_ok_response(content)


class TestUploadSettlementFile:
    @pytest.mark.asyncio
    async def test_atomic_partial_then_rename(self, tmp_path: Path):
        """Verify upload writes <name>.partial then renames to <name>."""
        local_file = tmp_path / "demo.txt"
        local_file.write_text("dummy", encoding="ascii")

        sftp_calls: list[tuple] = []

        class FakeSftp:
            async def put(self, src, dst):
                sftp_calls.append(("put", src, dst))

            async def rename(self, a, b):
                sftp_calls.append(("rename", a, b))

            async def remove(self, p):
                sftp_calls.append(("remove", p))

        @asynccontextmanager
        async def fake_session(**kwargs):
            yield FakeSftp()

        with patch.object(settlement_uploader, "_sftp_session", fake_session):
            ok = await upload_settlement_file(
                file_path=str(local_file),
                host="bank.example.com",
                username="parking",
                key_path="/keys/id_rsa",
                remote_dir="/incoming",
            )

        assert ok is True
        names = [c[0] for c in sftp_calls]
        assert "put" in names and "rename" in names
        put = next(c for c in sftp_calls if c[0] == "put")
        rename = next(c for c in sftp_calls if c[0] == "rename")
        assert put[2] == "/incoming/demo.txt.partial"
        assert rename[1] == "/incoming/demo.txt.partial"
        assert rename[2] == "/incoming/demo.txt"

    @pytest.mark.asyncio
    async def test_missing_file(self, tmp_path: Path):
        """Returns False if local file doesn't exist (no SFTP call)."""
        ok = await upload_settlement_file(
            file_path=str(tmp_path / "does-not-exist.txt"),
            host="bank.example.com",
            username="parking",
            key_path="/keys/id_rsa",
        )
        assert ok is False
