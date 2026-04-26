"""Tests for payment service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.models import Member, ParkingTransaction
from api.app.services.payment import (
    process_cash_payment,
    process_emoney_deduct,
    process_emoney_result,
    process_rfid_payment,
)
from api.app.services.transaction import create_entry_transaction
from shared.events import DeductStatus


@pytest_asyncio.fixture
async def active_transaction(db_session: AsyncSession) -> ParkingTransaction:
    tx = await create_entry_transaction(
        db_session,
        barcode="T100",
        plate_number="B1234XYZ",
        vehicle_type_id=None,
        payment_method="CASH",
    )
    return tx


@pytest_asyncio.fixture
async def active_member_transaction(db_session: AsyncSession) -> ParkingTransaction:
    member = Member(
        card_number="MEMBER01",
        name="Test Member",
        is_active=True,
        valid_from=datetime.now(timezone.utc).date(),
        valid_until=datetime(2099, 12, 31).date(),
    )
    db_session.add(member)
    await db_session.flush()
    await db_session.refresh(member)

    tx = await create_entry_transaction(
        db_session,
        card_number="MEMBER01",
        payment_method="RFID_MEMBER",
        member_id=member.id,
    )
    return tx


@pytest_asyncio.fixture
async def active_emoney_transaction(db_session: AsyncSession) -> ParkingTransaction:
    tx = await create_entry_transaction(
        db_session,
        card_number="EMONEY01",
        payment_method="EMONEY",
    )
    return tx


class TestProcessCashPayment:
    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_success(self, mock_publish, db_session: AsyncSession, active_transaction: ParkingTransaction):
        result = await process_cash_payment(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            barcode="T100",
            paid_amount=10000,
        )
        assert result["transaction"].status == "COMPLETED"
        assert result["transaction"].payment_method == "CASH"
        assert result["fee"] >= 0
        assert result["change_amount"] == 10000 - result["fee"]
        # Should publish open_gate and print_receipt
        assert mock_publish.call_count == 2

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_transaction_not_found(self, mock_publish, db_session: AsyncSession):
        with pytest.raises(ValueError, match="No active transaction found"):
            await process_cash_payment(
                db_session,
                gate_id="gate-out-1",
                gate_out_id=None,
                barcode="NONEXISTENT",
                paid_amount=10000,
            )

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_plate_lookup(self, mock_publish, db_session: AsyncSession, active_transaction: ParkingTransaction):
        result = await process_cash_payment(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            plate_number="B1234XYZ",
            paid_amount=5000,
        )
        assert result["transaction"].status == "COMPLETED"


class TestProcessRfidPayment:
    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_success(self, mock_publish, db_session: AsyncSession, active_member_transaction: ParkingTransaction):
        result = await process_rfid_payment(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            card_number="MEMBER01",
        )
        assert result["transaction"].status == "COMPLETED"
        assert result["transaction"].payment_method == "RFID_MEMBER"
        assert result["fee"] == 0
        assert result["member"] is not None
        # Should publish open_gate + play_audio
        assert mock_publish.call_count == 2

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_invalid_member(self, mock_publish, db_session: AsyncSession):
        with pytest.raises(ValueError, match="Invalid or inactive member card"):
            await process_rfid_payment(
                db_session,
                gate_id="gate-out-1",
                gate_out_id=None,
                card_number="INVALID",
            )

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_no_active_transaction(self, mock_publish, db_session: AsyncSession):
        member = Member(
            card_number="MEMBER02",
            name="Another Member",
            is_active=True,
        )
        db_session.add(member)
        await db_session.flush()

        with pytest.raises(ValueError, match="No active transaction found for this card"):
            await process_rfid_payment(
                db_session,
                gate_id="gate-out-1",
                gate_out_id=None,
                card_number="MEMBER02",
            )


class TestProcessEmoneyDeduct:
    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_success(self, mock_publish, db_session: AsyncSession, active_emoney_transaction: ParkingTransaction):
        result = await process_emoney_deduct(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            card_number="EMONEY01",
        )
        assert result["status"] == "PENDING"
        assert result["transaction"].payment_method == "PENDING"
        assert result["fee"] >= 0
        # Should publish deduct command
        assert mock_publish.call_count == 1

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_transaction_not_found(self, mock_publish, db_session: AsyncSession):
        with pytest.raises(ValueError, match="No active transaction found for this card"):
            await process_emoney_deduct(
                db_session,
                gate_id="gate-out-1",
                gate_out_id=None,
                card_number="INVALID",
            )


class TestProcessEmoneyResult:
    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_success(self, mock_publish, db_session: AsyncSession, active_emoney_transaction: ParkingTransaction):
        result = await process_emoney_result(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            card_number="EMONEY01",
            status=DeductStatus.SUCCESS,
            deduct_amount=5000,
            balance_before=50000,
            balance_after=45000,
            transaction_counter=42,
            raw_response_hex="EF0105...",
        )
        assert result["success"] is True
        assert result["transaction"].status == "COMPLETED"
        assert result["transaction"].payment_method == "EMONEY"
        assert result["emoney_transaction_id"] is not None
        # Should publish open_gate + print_receipt + play_audio
        assert mock_publish.call_count == 3

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_failed_status(self, mock_publish, db_session: AsyncSession, active_emoney_transaction: ParkingTransaction):
        result = await process_emoney_result(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            card_number="EMONEY01",
            status=DeductStatus.FAILED,
            deduct_amount=0,
            balance_before=50000,
            balance_after=50000,
            transaction_counter=0,
            raw_response_hex="EF0104...",
        )
        assert result["success"] is False
        assert result["transaction"].payment_method is None
        # Should not publish any commands on failure
        assert mock_publish.call_count == 0

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_insufficient_balance(self, mock_publish, db_session: AsyncSession, active_emoney_transaction: ParkingTransaction):
        result = await process_emoney_result(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            card_number="EMONEY01",
            status=DeductStatus.INSUFFICIENT_BALANCE,
            deduct_amount=0,
            balance_before=1000,
            balance_after=1000,
            transaction_counter=0,
            raw_response_hex="EF0104...",
        )
        assert result["success"] is False
        assert result["status"] == "INSUFFICIENT_BALANCE"

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_lost_contact_intermediate(self, mock_publish, db_session: AsyncSession, active_emoney_transaction: ParkingTransaction):
        """LOST_CONTACT should keep transaction in PENDING and publish display/audio."""
        result = await process_emoney_result(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            card_number="EMONEY01",
            status=DeductStatus.LOST_CONTACT,
            deduct_amount=0,
            balance_before=50000,
            balance_after=50000,
            transaction_counter=0,
            raw_response_hex="EF0105...",
        )
        assert result["success"] is False
        assert result["is_intermediate"] is True
        assert result["status"] == "LOST_CONTACT"
        # Transaction should NOT be reset (keep current payment method for retry)
        assert result["transaction"].payment_method == "EMONEY"
        # Should publish display_text + play_audio for retry prompt
        assert mock_publish.call_count == 2

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_correction_verified(self, mock_publish, db_session: AsyncSession, active_emoney_transaction: ParkingTransaction):
        """CORRECTION_VERIFIED should be treated as success."""
        result = await process_emoney_result(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            card_number="EMONEY01",
            status=DeductStatus.CORRECTION_VERIFIED,
            deduct_amount=5000,
            balance_before=50000,
            balance_after=45000,
            transaction_counter=43,
            raw_response_hex="EF0105...",
        )
        assert result["success"] is True
        assert result["transaction"].status == "COMPLETED"
        assert result["transaction"].payment_method == "EMONEY"
        # Should publish open_gate + print_receipt + play_audio
        assert mock_publish.call_count == 3

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_correction_failed(self, mock_publish, db_session: AsyncSession, active_emoney_transaction: ParkingTransaction):
        """CORRECTION_FAILED should reset transaction for other payment methods."""
        result = await process_emoney_result(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            card_number="EMONEY01",
            status=DeductStatus.CORRECTION_FAILED,
            deduct_amount=0,
            balance_before=50000,
            balance_after=50000,
            transaction_counter=0,
            raw_response_hex="EF0106...",
        )
        assert result["success"] is False
        assert result["transaction"].payment_method is None
        assert result["transaction"].fee is None
        # Should not publish any commands
        assert mock_publish.call_count == 0

    @patch("api.app.services.payment.publish_command", new_callable=AsyncMock)
    async def test_timeout(self, mock_publish, db_session: AsyncSession, active_emoney_transaction: ParkingTransaction):
        """TIMEOUT should reset transaction for other payment methods."""
        result = await process_emoney_result(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            card_number="EMONEY01",
            status=DeductStatus.TIMEOUT,
            deduct_amount=0,
            balance_before=50000,
            balance_after=50000,
            transaction_counter=0,
            raw_response_hex="",
        )
        assert result["success"] is False
        assert result["transaction"].payment_method is None
        # Should not publish any commands
        assert mock_publish.call_count == 0
