"""Tests for manual open log routes."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models.manual_open_log import ManualOpenLog
from api.app.models.user import User
from api.app.utils.password import hash_password
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
async def sample_operator(db_session: AsyncSession) -> User:
    user = User(
        username="operator1",
        email="op@test.com",
        full_name="Operator One",
        password_hash=hash_password("password"),
        role="operator",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_manual_open_log(db_session: AsyncSession, sample_operator: User) -> ManualOpenLog:
    log = ManualOpenLog(
        gate_id=1,
        gate_type="out",
        opened_by=sample_operator.id,
        reason="Gate malfunction",
        notes="Had to open manually",
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    return log


class TestListManualOpenLogs:
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/api/manual-open-logs")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_items(self, client: AsyncClient, sample_manual_open_log: ManualOpenLog):
        response = await client.get("/api/manual-open-logs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["reason"] == "Gate malfunction"
