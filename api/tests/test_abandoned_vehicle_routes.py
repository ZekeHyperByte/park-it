"""Tests for abandoned vehicle log routes."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models.abandoned_vehicle_log import AbandonedVehicleLog
from api.app.models.gate import Gate
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
async def sample_gate_out(db_session: AsyncSession) -> Gate:
    gate = Gate(
        name="Exit Gate",
        code="EXIT01",
        direction="OUT",
        protocol="compass",
        is_active=True,
    )
    db_session.add(gate)
    await db_session.commit()
    await db_session.refresh(gate)
    return gate


@pytest_asyncio.fixture
async def sample_abandoned_log(db_session: AsyncSession, sample_gate_out: Gate) -> AbandonedVehicleLog:
    log = AbandonedVehicleLog(
        gate_out_id=sample_gate_out.id,
        parking_transaction_id=None,
        waiting_seconds=125,
        resolution_type="VEHICLE_LEFT",
        notes="Vehicle left without paying",
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    return log


class TestListAbandonedVehicleLogs:
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/api/abandoned-vehicle-logs")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_items(self, client: AsyncClient, sample_abandoned_log: AbandonedVehicleLog):
        response = await client.get("/api/abandoned-vehicle-logs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["resolution_type"] == "VEHICLE_LEFT"
        assert data["items"][0]["waiting_seconds"] == 125
