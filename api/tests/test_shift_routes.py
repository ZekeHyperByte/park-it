"""Tests for shift routes."""

from datetime import time

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models.shift import Shift
from api.database import get_db


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Create a test client with DB override and mocked admin auth."""
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
async def sample_shift(db_session: AsyncSession) -> Shift:
    shift = Shift(
        name="Pagi",
        code="PAGI",
        start_time=time(6, 0),
        end_time=time(14, 0),
        is_active=True,
    )
    db_session.add(shift)
    await db_session.commit()
    await db_session.refresh(shift)
    return shift


class TestListShifts:
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/api/shifts")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_with_items(self, client: AsyncClient, sample_shift: Shift):
        response = await client.get("/api/shifts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Pagi"


class TestCreateShift:
    async def test_create_success(self, client: AsyncClient):
        response = await client.post("/api/shifts", json={
            "name": "Sore",
            "code": "SORE",
            "start_time": "14:00:00",
            "end_time": "22:00:00",
            "is_active": True,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Sore"
        assert data["code"] == "SORE"

    async def test_create_validation_error(self, client: AsyncClient):
        response = await client.post("/api/shifts", json={"name": ""})
        assert response.status_code == 422


class TestGetShift:
    async def test_get_by_id(self, client: AsyncClient, sample_shift: Shift):
        response = await client.get(f"/api/shifts/{sample_shift.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_shift.id

    async def test_get_not_found(self, client: AsyncClient):
        response = await client.get("/api/shifts/99999")
        assert response.status_code == 404


class TestUpdateShift:
    async def test_update_success(self, client: AsyncClient, sample_shift: Shift):
        response = await client.patch(f"/api/shifts/{sample_shift.id}", json={
            "name": "Pagi Updated",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Pagi Updated"
        assert data["code"] == "PAGI"

    async def test_update_not_found(self, client: AsyncClient):
        response = await client.patch("/api/shifts/99999", json={"name": "X"})
        assert response.status_code == 404


class TestDeleteShift:
    async def test_delete_success(self, client: AsyncClient, sample_shift: Shift):
        response = await client.delete(f"/api/shifts/{sample_shift.id}")
        assert response.status_code == 200

        response = await client.get(f"/api/shifts/{sample_shift.id}")
        assert response.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient):
        response = await client.delete("/api/shifts/99999")
        assert response.status_code == 404
