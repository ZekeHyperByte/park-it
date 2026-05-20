"""Tests for transaction routes."""

from datetime import datetime, timezone

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models.parking_transaction import ParkingTransaction
from api.app.models.vehicle_type import VehicleType
from api.database import get_db


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    from fastapi import Request
    from api.app.middleware.auth import require_operator

    async def mock_require_operator(request: Request):
        return {"sub": "1", "username": "operator", "role": "operator"}

    app.dependency_overrides[require_operator] = mock_require_operator

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
async def sample_transaction(db_session: AsyncSession, sample_vehicle_type: VehicleType) -> ParkingTransaction:
    tx = ParkingTransaction(
        barcode="ABC123",
        plate_number="B1234ABC",
        vehicle_type_id=sample_vehicle_type.id,
        entry_time=datetime(2026, 4, 25, 10, 0, 0, tzinfo=timezone.utc),
        payment_method="CASH",
        fee=5000,
        paid_amount=10000,
        status="COMPLETED",
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)
    return tx


class TestListTransactions:
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/api/transactions")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_with_items(self, client: AsyncClient, sample_transaction: ParkingTransaction):
        response = await client.get("/api/transactions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["barcode"] == "ABC123"
        assert data[0]["status"] == "COMPLETED"

    async def test_list_search(self, client: AsyncClient, sample_transaction: ParkingTransaction):
        response = await client.get("/api/transactions?q=ABC123")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        response = await client.get("/api/transactions?q=NONEXISTENT")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_list_filter_by_status(self, client: AsyncClient, sample_transaction: ParkingTransaction):
        response = await client.get("/api/transactions?status=COMPLETED")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        response = await client.get("/api/transactions?status=ACTIVE")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_list_filter_by_date(self, client: AsyncClient, sample_transaction: ParkingTransaction):
        response = await client.get("/api/transactions?date_from=2026-04-01&date_to=2026-05-01")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        response = await client.get("/api/transactions?date_from=2025-01-01&date_to=2025-02-01")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestGetTransaction:
    async def test_get_by_id(self, client: AsyncClient, sample_transaction: ParkingTransaction):
        response = await client.get(f"/api/transactions/{sample_transaction.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_transaction.id
        assert data["barcode"] == "ABC123"
        assert data["duration_minutes"] is None  # exit_time is None

    async def test_get_not_found(self, client: AsyncClient):
        response = await client.get("/api/transactions/99999")
        assert response.status_code == 404
