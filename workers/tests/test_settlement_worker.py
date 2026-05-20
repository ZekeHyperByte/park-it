import pytest
import tempfile
from unittest.mock import AsyncMock, patch

from workers.background import settlement_worker
from workers.background.settlement_worker import generate_settlement_file


class TestGenerateSettlementFile:
    @pytest.fixture(autouse=True)
    def setup_settlement_dir(self):
        """Use temp dir for settlement files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(settlement_worker, "SETTLEMENT_DIR", tmpdir):
                yield tmpdir

    @pytest.mark.asyncio
    async def test_no_unsettled_transactions(self):
        """When no unsettled SUCCESS transactions exist, return empty result."""
        mock_ctx = {"redis": AsyncMock()}
        result = await generate_settlement_file(mock_ctx)
        assert result["status"] == "success"
        assert result["files_generated"] == 0
        assert result["total_transactions"] == 0
        assert isinstance(result, dict)
