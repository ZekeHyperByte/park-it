import os
import pytest
import tempfile
from unittest.mock import patch

from sqlalchemy import select

from api.app.models.emoney_reader import EmoneyReader
from api.app.models.emoney_transaction import EmoneyTransaction
from api.app.models.emoney_settlement import EmoneySettlement
from workers.background import settlement_worker
from workers.background.settlement_worker import generate_settlement_file


class TestSettlementGeneration:
    @pytest.fixture(autouse=True)
    def setup_settlement_dir(self):
        """Use temp dir for settlement files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(settlement_worker, "SETTLEMENT_DIR", tmpdir):
                yield tmpdir

    @pytest.mark.asyncio
    async def test_settlement_file_format(self, db_session):
        """Create transactions, run settlement worker, verify file format."""
        # Create reader with MID/TID
        reader = EmoneyReader(
            name="Test Reader",
            code="TEST001",
            serial_port="/dev/ttyUSB0",
            mid="2034567890ABCDE",
            tid="87654321",
            is_active=True,
        )
        db_session.add(reader)
        await db_session.flush()

        # Create SUCCESS transactions
        for i in range(3):
            tx = EmoneyTransaction(
                card_number=f"1234567890{i}",
                card_type="MANDIRI",
                amount_deducted=500 * (i + 1),
                status="SUCCESS",
                emoney_reader_id=reader.id,
                raw_response_hex=f"0102034567890ABCDE8765432110122017121550571012062017000{i}0000000{i+1}00D0CC",
            )
            db_session.add(tx)

        await db_session.commit()

        # Run settlement worker with injected test DB session
        result = await generate_settlement_file({}, db=db_session)
        assert result["status"] == "success"
        assert result["files_generated"] == 1
        assert result["total_transactions"] == 3

        # Verify DB record
        settlement = await db_session.scalar(select(EmoneySettlement))
        assert settlement is not None
        assert settlement.total_transactions == 3
        assert settlement.total_amount == 500 + 1000 + 1500
        assert settlement.status == "GENERATED"

        # Verify filename format
        assert len(settlement.filename) == 47  # 14 + 16 + 8 + 2 + 3 + 4
        assert settlement.filename.endswith(".txt")
        assert settlement.filename[14:30] == "02034567890ABCDE"  # MID
        assert settlement.filename[30:38] == "87654321"  # TID

        # Verify file content
        assert settlement.file_path is not None
        assert os.path.exists(settlement.file_path)

        with open(settlement.file_path, "r") as f:
            content = f.read()

        lines = content.strip().split("\n")
        assert lines[0] == "0030000003000"  # 3 transactions, total 3000
        assert len(lines) == 4  # header + 3 transactions + empty

        # Verify transactions linked
        tx_result = await db_session.execute(
            select(EmoneyTransaction).where(
                EmoneyTransaction.settlement_batch_id == settlement.id
            )
        )
        linked = tx_result.scalars().all()
        assert len(linked) == 3

    @pytest.mark.asyncio
    async def test_no_transactions_no_file(self, db_session):
        """When no unsettled transactions exist, no file generated."""
        result = await generate_settlement_file({}, db=db_session)
        assert result["files_generated"] == 0
        assert result["total_transactions"] == 0
