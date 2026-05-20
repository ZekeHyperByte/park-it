"""Tests for area routes."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models.area_parkir import AreaParkir
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
async def sample_area(db_session: AsyncSession) -> AreaParkir:
    area = AreaParkir(
        name="Area A",
        code="A01",
        capacity=100,
        current=0,
    )
    db_session.add(area)
    await db_session.commit()
    await db_session.refresh(area)
    return area


class TestListAreas:
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/api/areas")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_with_items(self, client: AsyncClient, sample_area: AreaParkir):
        response = await client.get("/api/areas")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Area A"


class TestCreateArea:
    async def test_create_success(self, client: AsyncClient):
        response = await client.post("/api/areas", json={
            "name": "Area B",
            "code": "B01",
            "capacity": 50,
            "current": 0,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Area B"
        assert data["code"] == "B01"

    async def test_create_validation_error(self, client: AsyncClient):
        response = await client.post("/api/areas", json={"name": ""})
        assert response.status_code == 422


class TestGetArea:
    async def test_get_by_id(self, client: AsyncClient, sample_area: AreaParkir):
        response = await client.get(f"/api/areas/{sample_area.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_area.id

    async def test_get_not_found(self, client: AsyncClient):
        response = await client.get("/api/areas/99999")
        assert response.status_code == 404


class TestUpdateArea:
    async def test_update_success(self, client: AsyncClient, sample_area: AreaParkir):
        response = await client.patch(f"/api/areas/{sample_area.id}", json={
            "name": "Area A Updated",
            "capacity": 150,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Area A Updated"
        assert data["capacity"] == 150

    async def test_update_not_found(self, client: AsyncClient):
        response = await client.patch("/api/areas/99999", json={"name": "X"})
        assert response.status_code == 404


class TestDeleteArea:
    async def test_delete_success(self, client: AsyncClient, sample_area: AreaParkir):
        response = await client.delete(f"/api/areas/{sample_area.id}")
        assert response.status_code == 200

        response = await client.get(f"/api/areas/{sample_area.id}")
        assert response.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient):
        response = await client.delete("/api/areas/99999")
        assert response.status_code == 404
