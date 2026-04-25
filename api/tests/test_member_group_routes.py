"""Tests for member group routes."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models.member_group import MemberGroup
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
async def sample_member_group(db_session: AsyncSession) -> MemberGroup:
    group = MemberGroup(
        name="Regular",
        code="REG",
        description="Regular members",
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    return group


class TestListMemberGroups:
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/api/member-groups")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_with_items(self, client: AsyncClient, sample_member_group: MemberGroup):
        response = await client.get("/api/member-groups")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Regular"


class TestCreateMemberGroup:
    async def test_create_success(self, client: AsyncClient):
        response = await client.post("/api/member-groups", json={
            "name": "VIP",
            "code": "VIP",
            "description": "VIP members",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "VIP"
        assert data["code"] == "VIP"

    async def test_create_validation_error(self, client: AsyncClient):
        response = await client.post("/api/member-groups", json={"name": ""})
        assert response.status_code == 422


class TestGetMemberGroup:
    async def test_get_by_id(self, client: AsyncClient, sample_member_group: MemberGroup):
        response = await client.get(f"/api/member-groups/{sample_member_group.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_member_group.id

    async def test_get_not_found(self, client: AsyncClient):
        response = await client.get("/api/member-groups/99999")
        assert response.status_code == 404


class TestUpdateMemberGroup:
    async def test_update_success(self, client: AsyncClient, sample_member_group: MemberGroup):
        response = await client.patch(f"/api/member-groups/{sample_member_group.id}", json={
            "name": "Regular Updated",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Regular Updated"
        assert data["code"] == "REG"

    async def test_update_not_found(self, client: AsyncClient):
        response = await client.patch("/api/member-groups/99999", json={"name": "X"})
        assert response.status_code == 404


class TestDeleteMemberGroup:
    async def test_delete_success(self, client: AsyncClient, sample_member_group: MemberGroup):
        response = await client.delete(f"/api/member-groups/{sample_member_group.id}")
        assert response.status_code == 200

        response = await client.get(f"/api/member-groups/{sample_member_group.id}")
        assert response.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient):
        response = await client.delete("/api/member-groups/99999")
        assert response.status_code == 404
