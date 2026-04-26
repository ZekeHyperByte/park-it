import pytest

from workers.background.settlement_uploader import parse_ok_response, parse_nok_response


class TestParseOkResponse:
    def test_single_accepted(self):
        content = "01002\nAABBCC00\n"
        result = parse_ok_response(content)
        assert len(result) == 1
        assert result[0]["status"] == "00"
        assert result[0]["raw_data"] == "AABBCC"

    def test_multiple_mixed(self):
        content = "01003\nAABBCC00\nDDEEFF01\nGGHHII00\n"
        result = parse_ok_response(content)
        assert len(result) == 3
        assert result[0]["status"] == "00"
        assert result[1]["status"] == "01"
        assert result[2]["status"] == "00"


class TestParseNokResponse:
    def test_rejected_header(self):
        content = "01001\nAABBCC04\n"
        result = parse_nok_response(content)
        assert len(result) == 1
        assert result[0]["status"] == "04"
