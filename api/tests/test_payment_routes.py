"""Tests for payment routes."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models import Member, ParkingTransaction
from api.app.services.transaction import create_entry_transaction
from api.database import get_db


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Create a test client with DB override."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Mock auth middleware to always return operator user
    from api.app.middleware import auth as auth_module
    original_require_operator = auth_module.require_operator

    async def mock_require_operator(request):
        return {"sub": "1", "username": "operator", "role": "operator"}

    auth_module.require_operator = mock_require_operator

    # Also need to patch get_current_user for the middleware
    original_get_current_user = auth_module.get_current_user

    async def mock_get_current_user(request):
        return {"sub": "1", "username": "operator", "role": "operator"}

    auth_module.get_current_user = mock_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    # Restore
    app.dependency_overrides.clear()
    auth_module.require_operator = original_require_operator
    auth_module.get_current_user = original_get_current_user


@pytest_asyncio.fixture
async def sample_transaction(db_session: AsyncSession) -> ParkingTransaction:
    tx = await create_entry_transaction(
        db_session,
        barcode="RT100",
        plate_number="B9999ZZ",
        payment_method="CASH",
    )
    return tx


class TestCashPayment:
    @patch("api.app.routes.payments.process_cash_payment")
    async def test_cash_payment_success(self, mock_process, client: AsyncClient, sample_transaction: ParkingTransaction):
        mock_process.return_value = {
            "transaction": sample_transaction,
            "fee": 5000,
            "change_amount": 5000,
        }

        response = await client.post("/api/payments/cash", json={
            "gate_id": "gate-out-1",
            "gate_out_id": 1,
            "barcode": "RT100",
            "paid_amount": 10000,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["fee"] == 5000
        assert data["change_amount"] == 5000
        assert data["payment_method"] == "CASH"

    @patch("api.app.routes.payments.process_cash_payment")
    async def test_cash_payment_failure(self, mock_process, client: AsyncClient):
        mock_process.side_effect = ValueError("No active transaction found")

        response = await client.post("/api/payments/cash", json={
            "gate_id": "gate-out-1",
            "gate_out_id": 1,
            "barcode": "INVALID",
            "paid_amount": 10000,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No active transaction found" in data["message"]


class TestRfidPayment:
    @patch("api.app.routes.payments.process_rfid_payment")
    async def test_rfid_payment_success(self, mock_process, client: AsyncClient, sample_transaction: ParkingTransaction):
        mock_process.return_value = {
            "transaction": sample_transaction,
            "fee": 0,
            "member": None,
        }

        response = await client.post("/api/payments/rfid", json={
            "gate_id": "gate-out-1",
            "gate_out_id": 1,
            "card_number": "MEMBER01",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["fee"] == 0
        assert data["payment_method"] == "RFID_MEMBER"


class TestEmoneyDeduct:
    @patch("api.app.routes.payments.process_emoney_deduct")
    async def test_emoney_deduct_success(self, mock_process, client: AsyncClient, sample_transaction: ParkingTransaction):
        mock_process.return_value = {
            "transaction": sample_transaction,
            "fee": 5000,
            "status": "PENDING",
        }

        response = await client.post("/api/payments/emoney/deduct", json={
            "gate_id": "gate-out-1",
            "gate_out_id": 1,
            "card_number": "EMONEY01",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["payment_method"] == "PENDING"


class TestEmoneyResult:
    @patch("api.app.routes.payments.process_emoney_result")
    async def test_emoney_result_success(self, mock_process, client: AsyncClient, sample_transaction: ParkingTransaction):
        mock_process.return_value = {
            "transaction": sample_transaction,
            "emoney_transaction_id": 99,
            "success": True,
            "status": "SUCCESS",
        }

        response = await client.post("/api/payments/emoney/result", json={
            "gate_id": "gate-out-1",
            "gate_out_id": 1,
            "card_number": "EMONEY01",
            "status": "SUCCESS",
            "deduct_amount": 5000,
            "balance_before": 50000,
            "balance_after": 45000,
            "transaction_counter": 42,
            "raw_response_hex": "EF0105...",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_emoney_result_invalid_status(self, client: AsyncClient):
        response = await client.post("/api/payments/emoney/result", json={
            "gate_id": "gate-out-1",
            "gate_out_id": 1,
            "card_number": "EMONEY01",
            "status": "INVALID_STATUS",
            "deduct_amount": 0,
            "balance_before": 0,
            "balance_after": 0,
            "transaction_counter": 0,
            "raw_response_hex": "",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Invalid deduct status" in data["message"]


class TestLookupTransaction:
    async def test_lookup_by_barcode_found(self, client: AsyncClient, sample_transaction: ParkingTransaction):
        response = await client.post("/api/payments/lookup", json={
            "barcode": "RT100",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["transaction"]["barcode"] == "RT100"
        assert data["fee"] is not None

    async def test_lookup_not_found(self, client: AsyncClient):
        response = await client.post("/api/payments/lookup", json={
            "barcode": "NONEXISTENT",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is False
        assert data["transaction"] is None
