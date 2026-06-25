"""Tests for emoney reader routes."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models.emoney_reader import EmoneyReader
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
async def sample_emoney_reader(db_session: AsyncSession) -> EmoneyReader:
    reader = EmoneyReader(
        name="Reader 1",
        code="R01",
        serial_port="/dev/ttyUSB0",
        baudrate=38400,
        mid="D021095711020001",
        tid="09570004",
    )
    db_session.add(reader)
    await db_session.commit()
    await db_session.refresh(reader)
    return reader


class TestListEmoneyReaders:
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/api/emoney-readers")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_with_items(self, client: AsyncClient, sample_emoney_reader: EmoneyReader):
        response = await client.get("/api/emoney-readers")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Reader 1"


class TestCreateEmoneyReader:
    async def test_create_success(self, client: AsyncClient):
        response = await client.post("/api/emoney-readers", json={
            "name": "Reader 2",
            "code": "R02",
            "serial_port": "/dev/ttyUSB1",
            "baudrate": 38400,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Reader 2"
        assert data["code"] == "R02"

    async def test_create_validation_error(self, client: AsyncClient):
        response = await client.post("/api/emoney-readers", json={"name": ""})
        assert response.status_code == 422


class TestGetEmoneyReader:
    async def test_get_by_id(self, client: AsyncClient, sample_emoney_reader: EmoneyReader):
        response = await client.get(f"/api/emoney-readers/{sample_emoney_reader.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_emoney_reader.id

    async def test_get_not_found(self, client: AsyncClient):
        response = await client.get("/api/emoney-readers/99999")
        assert response.status_code == 404


class TestUpdateEmoneyReader:
    async def test_update_success(self, client: AsyncClient, sample_emoney_reader: EmoneyReader):
        response = await client.patch(f"/api/emoney-readers/{sample_emoney_reader.id}", json={
            "name": "Reader 1 Updated",
            "baudrate": 115200,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Reader 1 Updated"
        assert data["baudrate"] == 115200

    async def test_update_not_found(self, client: AsyncClient):
        response = await client.patch("/api/emoney-readers/99999", json={"name": "X"})
        assert response.status_code == 404


class TestDeleteEmoneyReader:
    async def test_delete_success(self, client: AsyncClient, sample_emoney_reader: EmoneyReader):
        response = await client.delete(f"/api/emoney-readers/{sample_emoney_reader.id}")
        assert response.status_code == 200

        response = await client.get(f"/api/emoney-readers/{sample_emoney_reader.id}")
        assert response.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient):
        response = await client.delete("/api/emoney-readers/99999")
        assert response.status_code == 404
