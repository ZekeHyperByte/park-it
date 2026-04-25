"""Tests for report routes."""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models.emoney_transaction import EmoneyTransaction
from api.app.models.parking_transaction import ParkingTransaction
from api.app.models.vehicle_type import VehicleType
from api.database import get_db


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    from fastapi import Request
    from api.app.middleware.auth import require_admin

    async def mock_require_admin(request: Request):
        return {"sub": "1", "username": "admin", "role": "admin"}

    app.dependency_overrides[require_admin] = mock_require_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_vehicle_type(db_session: AsyncSession) -> VehicleType:
    vt = VehicleType(name="Motor", code="MOTOR", base_tariff=2000, hourly_rate=1000, max_daily_cap=15000)
    db_session.add(vt)
    await db_session.commit()
    await db_session.refresh(vt)
    return vt


@pytest_asyncio.fixture
async def seeded_transactions(db_session: AsyncSession, sample_vehicle_type: VehicleType):
    """Seed transactions for report testing."""
    txs = [
        ParkingTransaction(
            barcode="CASH01",
            plate_number="B1111AA",
            vehicle_type_id=sample_vehicle_type.id,
            entry_time=datetime(2026, 4, 25, 10, 0, 0, tzinfo=timezone.utc),
            payment_method="CASH",
            fee=5000,
            paid_amount=5000,
            status="COMPLETED",
        ),
        ParkingTransaction(
            barcode="CASH02",
            plate_number="B2222BB",
            vehicle_type_id=sample_vehicle_type.id,
            entry_time=datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc),
            payment_method="CASH",
            fee=3000,
            paid_amount=3000,
            status="COMPLETED",
        ),
        ParkingTransaction(
            barcode="EMONEY01",
            plate_number="B3333CC",
            vehicle_type_id=sample_vehicle_type.id,
            entry_time=datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc),
            payment_method="EMONEY",
            fee=5000,
            paid_amount=5000,
            status="COMPLETED",
        ),
        ParkingTransaction(
            barcode="RFID01",
            plate_number="B4444DD",
            vehicle_type_id=sample_vehicle_type.id,
            entry_time=datetime(2026, 4, 25, 13, 0, 0, tzinfo=timezone.utc),
            payment_method="RFID_MEMBER",
            fee=0,
            paid_amount=0,
            status="COMPLETED",
        ),
        ParkingTransaction(
            barcode="ACTIVE01",
            plate_number="B5555EE",
            vehicle_type_id=sample_vehicle_type.id,
            entry_time=datetime(2026, 4, 25, 14, 0, 0, tzinfo=timezone.utc),
            status="ACTIVE",
        ),
    ]
    for tx in txs:
        db_session.add(tx)
    await db_session.commit()

    # Emoney transactions
    em_txs = [
        EmoneyTransaction(
            card_number="5715048100000048",
            card_type="MANDIRI",
            amount_deducted=5000,
            balance_before=100000,
            balance_after=95000,
            status="SUCCESS",
            raw_response_hex="EF0105...",
        ),
        EmoneyTransaction(
            card_number="5715048100000049",
            card_type="BRI",
            amount_deducted=3000,
            balance_before=50000,
            balance_after=47000,
            status="SUCCESS",
        ),
        EmoneyTransaction(
            card_number="5715048100000050",
            card_type="BNI",
            amount_deducted=0,
            balance_before=0,
            balance_after=0,
            status="LOST_CONTACT",
        ),
    ]
    for em in em_txs:
        db_session.add(em)
    await db_session.commit()

    return txs


class TestSummaryReport:
    async def test_summary_report(self, client: AsyncClient, seeded_transactions):
        response = await client.get("/api/reports/summary?date_from=2026-04-01&date_to=2026-05-01")
        assert response.status_code == 200
        data = response.json()
        assert data["total_transactions"] == 5
        assert data["total_revenue"] == 13000
        assert data["cash_revenue"] == 8000
        assert data["emoney_revenue"] == 5000
        assert data["rfid_revenue"] == 0
        assert data["active_transactions"] == 1
        assert data["completed_transactions"] == 4
        assert data["average_fee"] == 2600.0

    async def test_summary_report_no_data(self, client: AsyncClient):
        response = await client.get("/api/reports/summary?date_from=2025-01-01&date_to=2025-02-01")
        assert response.status_code == 200
        data = response.json()
        assert data["total_transactions"] == 0
        assert data["total_revenue"] == 0
        assert data["average_fee"] == 0

    async def test_summary_report_requires_dates(self, client: AsyncClient):
        response = await client.get("/api/reports/summary")
        assert response.status_code == 422


class TestEmoneyReport:
    async def test_emoney_report(self, client: AsyncClient, seeded_transactions):
        response = await client.get("/api/reports/emoney?date_from=2026-04-01&date_to=2026-05-01")
        assert response.status_code == 200
        data = response.json()
        assert data["total_emoney_transactions"] == 3
        assert data["total_deducted"] == 8000
        assert data["success_count"] == 2
        assert data["lost_contact_count"] == 1
        assert data["failed_count"] == 0
        assert data["average_deduct_amount"] == 2666.67

    async def test_emoney_report_no_data(self, client: AsyncClient):
        response = await client.get("/api/reports/emoney?date_from=2025-01-01&date_to=2025-02-01")
        assert response.status_code == 200
        data = response.json()
        assert data["total_emoney_transactions"] == 0
        assert data["total_deducted"] == 0
        assert data["average_deduct_amount"] == 0
