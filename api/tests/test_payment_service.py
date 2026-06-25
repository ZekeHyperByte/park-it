"""Tests for payment service."""

from datetime import datetime, timedelta, timezone
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
async def emoney_ticket_transaction(db_session: AsyncSession) -> ParkingTransaction:
    """E-money entries no longer exist; tickets enter as CASH and the card is presented at exit."""
    tx = await create_entry_transaction(
        db_session,
        barcode="EM100",
        payment_method="CASH",
    )
    return tx


class TestProcessCashPayment:
    async def test_success(self, db_session: AsyncSession, active_transaction: ParkingTransaction):
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

    async def test_rejects_underpayment(
        self, db_session: AsyncSession, active_transaction: ParkingTransaction
    ):
        """Cash exit must not complete when paid_amount < fee."""
        # Backdate entry 2h so the default (MOBIL) tariff yields a non-zero fee.
        active_transaction.entry_time = datetime.now(timezone.utc) - timedelta(hours=2)
        await db_session.flush()
        with pytest.raises(ValueError, match="Insufficient payment"):
            await process_cash_payment(
                db_session,
                gate_id="gate-out-1",
                gate_out_id=None,
                barcode="T100",
                paid_amount=1,
            )
        assert active_transaction.status == "ACTIVE"

    async def test_transaction_not_found(self, db_session: AsyncSession):
        with pytest.raises(ValueError, match="No active transaction found"):
            await process_cash_payment(
                db_session,
                gate_id="gate-out-1",
                gate_out_id=None,
                barcode="NONEXISTENT",
                paid_amount=10000,
            )

    async def test_plate_lookup(self, db_session: AsyncSession, active_transaction: ParkingTransaction):
        result = await process_cash_payment(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            plate_number="B1234XYZ",
            paid_amount=5000,
        )
        assert result["transaction"].status == "COMPLETED"


class TestProcessRfidPayment:
    async def test_success(self, db_session: AsyncSession, active_member_transaction: ParkingTransaction):
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

    async def test_invalid_member(self, db_session: AsyncSession):
        with pytest.raises(ValueError, match="Invalid or inactive member card"):
            await process_rfid_payment(
                db_session,
                gate_id="gate-out-1",
                gate_out_id=None,
                card_number="INVALID",
            )

    async def test_no_active_transaction(self, db_session: AsyncSession):
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
    @patch("api.app.services.payment._set_emoney_pending", new_callable=AsyncMock)
    async def test_success(
        self, mock_set, db_session: AsyncSession, emoney_ticket_transaction: ParkingTransaction
    ):
        result = await process_emoney_deduct(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            barcode="EM100",
        )
        assert result["status"] == "ARMED"
        assert result["fee"] >= 0
        mock_set.assert_awaited_once()

    @patch("api.app.services.payment._set_emoney_pending", new_callable=AsyncMock)
    async def test_transaction_not_found(self, mock_set, db_session: AsyncSession):
        with pytest.raises(ValueError, match="No active transaction found for this ticket"):
            await process_emoney_deduct(
                db_session,
                gate_id="gate-out-1",
                gate_out_id=None,
                barcode="NONEXISTENT",
            )


class TestProcessEmoneyResult:
    @pytest_asyncio.fixture
    async def pending(self, emoney_ticket_transaction: ParkingTransaction):
        return {
            "transaction_id": emoney_ticket_transaction.id,
            "gate_out_id": None,
            "fee": 5000,
        }

    @patch("api.app.services.payment._clear_emoney_pending", new_callable=AsyncMock)
    @patch("api.app.services.payment._get_emoney_pending", new_callable=AsyncMock)
    async def test_success(
        self, mock_get, mock_clear, pending, db_session: AsyncSession,
        emoney_ticket_transaction: ParkingTransaction,
    ):
        mock_get.return_value = pending
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
        assert result["transaction"].card_number == "EMONEY01"
        mock_clear.assert_awaited_once()

    @patch("api.app.services.payment._clear_emoney_pending", new_callable=AsyncMock)
    @patch("api.app.services.payment._get_emoney_pending", new_callable=AsyncMock)
    async def test_failed_falls_back_to_cash_friendly(
        self, mock_get, mock_clear, pending, db_session: AsyncSession,
        emoney_ticket_transaction: ParkingTransaction,
    ):
        mock_get.return_value = pending
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
        # Transaction stays ACTIVE so cash fallback works
        assert result["transaction"].status == "ACTIVE"
        mock_clear.assert_awaited_once()

    @patch("api.app.services.payment._clear_emoney_pending", new_callable=AsyncMock)
    @patch("api.app.services.payment._get_emoney_pending", new_callable=AsyncMock)
    async def test_lost_contact_keeps_pending(
        self, mock_get, mock_clear, pending, db_session: AsyncSession,
        emoney_ticket_transaction: ParkingTransaction,
    ):
        mock_get.return_value = pending
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
        # Pending state is preserved so operator can ask driver to re-tap.
        mock_clear.assert_not_awaited()

    @patch("api.app.services.payment._get_emoney_pending", new_callable=AsyncMock)
    async def test_no_pending_state(self, mock_get, db_session: AsyncSession):
        mock_get.return_value = None
        with pytest.raises(ValueError, match="No pending e-money deduct"):
            await process_emoney_result(
                db_session,
                gate_id="gate-out-1",
                gate_out_id=None,
                card_number="EMONEY01",
                status=DeductStatus.SUCCESS,
                deduct_amount=5000,
                balance_before=50000,
                balance_after=45000,
                transaction_counter=42,
                raw_response_hex="",
            )

    @patch("api.app.services.payment._clear_emoney_pending", new_callable=AsyncMock)
    @patch("api.app.services.payment._get_emoney_pending", new_callable=AsyncMock)
    async def test_cash_fallback_after_emoney_failure(
        self, mock_get, mock_clear, pending, db_session: AsyncSession,
        emoney_ticket_transaction: ParkingTransaction,
    ):
        """After an INSUFFICIENT_BALANCE result, cash payment on the same ticket must succeed."""
        mock_get.return_value = pending
        await process_emoney_result(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            card_number="EMONEY01",
            status=DeductStatus.INSUFFICIENT_BALANCE,
            deduct_amount=0,
            balance_before=1000,
            balance_after=1000,
            transaction_counter=0,
            raw_response_hex="",
        )
        result = await process_cash_payment(
            db_session,
            gate_id="gate-out-1",
            gate_out_id=None,
            barcode="EM100",
            paid_amount=10000,
        )
        assert result["transaction"].status == "COMPLETED"
        assert result["transaction"].payment_method == "CASH"
