"""End-to-end settlement worker tests against Multibank v1.3 §I."""

import os
import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy import select

from api.app.models.emoney_reader import EmoneyReader
from api.app.models.emoney_settlement import EmoneySettlement
from api.app.models.emoney_transaction import EmoneyTransaction
from workers.background import settlement_worker
from workers.background.settlement_worker import generate_settlement_file


# A valid 40-byte deduct response payload (cardtype..counter), no card log.
def _payload(card_type_code: int = 0x02, suffix: str = "00") -> str:
    """Build a fake settlement_payload_hex (cardtype..counter) for testing."""
    return (
        f"{card_type_code:02X}"
        "02034567890ABCDE"  # MID (8 bytes)
        "87654321"  # TID (4 bytes)
        "10122017121550"  # DateTime BCD (7 bytes)
        f"57101206201700{suffix}"  # CardNo (8 bytes)
        "00000001"  # Deducted (4 bytes)
        "0001D0CC"  # Remaining (4 bytes)
        "00000001"  # Counter (4 bytes)
    )


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

        # Create SUCCESS transactions. Per Multibank v1.3 §I, settlement uses
        # settlement_payload_hex (cardtype..CardLog body), not the full PASSTI
        # frame in raw_response_hex.
        for i in range(3):
            tx = EmoneyTransaction(
                card_number=f"1234567890{i}",
                card_type="Mandiri eMoney",
                card_type_code=0x02,
                amount_deducted=500 * (i + 1),
                status="SUCCESS",
                emoney_reader_id=reader.id,
                raw_response_hex=f"02XX{i:02d}",
                settlement_payload_hex=_payload(0x02, f"{i:02X}"),
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

        with open(settlement.file_path) as f:
            content = f.read()

        lines = content.strip().split("\n")
        assert lines[0] == "0030000003000"  # 3 transactions, total 3000
        assert len(lines) == 4  # header + 3 transactions

        # Each body line must start with the cardtype byte (02 = Mandiri),
        # not the PASSTI STX (02 too, but here verified by full prefix).
        for line in lines[1:]:
            assert line.startswith("02"), (
                "Settlement line must start with cardtype byte per Multibank v1.3 §I"
            )

        # Verify transactions linked
        tx_result = await db_session.execute(
            select(EmoneyTransaction).where(
                EmoneyTransaction.settlement_batch_id == settlement.id
            )
        )
        linked = tx_result.scalars().all()
        assert len(linked) == 3

    @pytest.mark.asyncio
    async def test_qr_payment_excluded(self, db_session):
        """Multibank v1.3: cardtype 09 (QR Payment) is excluded from settlement."""
        reader = EmoneyReader(
            name="Test Reader QR",
            code="TESTQR",
            serial_port="/dev/ttyUSB1",
            mid="2034567890ABCDEF",
            tid="00000099",
            is_active=True,
        )
        db_session.add(reader)
        await db_session.flush()

        # 1 eMoney + 1 QR — only eMoney should settle.
        db_session.add(EmoneyTransaction(
            card_number="EMONEY01",
            card_type="Mandiri eMoney",
            card_type_code=0x02,
            amount_deducted=5000,
            status="SUCCESS",
            emoney_reader_id=reader.id,
            settlement_payload_hex=_payload(0x02, "11"),
        ))
        db_session.add(EmoneyTransaction(
            card_number="QR0001",
            card_type="QR Payment",
            card_type_code=0x09,
            amount_deducted=3000,
            status="SUCCESS",
            emoney_reader_id=reader.id,
            settlement_payload_hex=_payload(0x09, "22"),
        ))
        await db_session.commit()

        result = await generate_settlement_file({}, db=db_session)
        assert result["files_generated"] == 1
        assert result["total_transactions"] == 1  # QR excluded

        settlement = await db_session.scalar(select(EmoneySettlement))
        assert settlement is not None
        assert settlement.total_transactions == 1
        assert settlement.total_amount == 5000  # QR amount excluded

        # The QR transaction must NOT have settlement_batch_id set.
        qr_tx = await db_session.scalar(
            select(EmoneyTransaction).where(EmoneyTransaction.card_number == "QR0001")
        )
        assert qr_tx.settlement_batch_id is None

        em_tx = await db_session.scalar(
            select(EmoneyTransaction).where(EmoneyTransaction.card_number == "EMONEY01")
        )
        assert em_tx.settlement_batch_id == settlement.id

    @pytest.mark.asyncio
    async def test_no_transactions_no_file(self, db_session):
        """When no unsettled transactions exist, no file generated."""
        result = await generate_settlement_file({}, db=db_session)
        assert result["files_generated"] == 0
        assert result["total_transactions"] == 0
