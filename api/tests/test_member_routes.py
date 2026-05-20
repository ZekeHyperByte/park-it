"""Tests for member routes."""

from datetime import date

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models.member import Member
from api.app.models.member_group import MemberGroup
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
async def sample_member_group(db_session: AsyncSession) -> MemberGroup:
    group = MemberGroup(name="Regular", code="REG")
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    return group


@pytest_asyncio.fixture
async def sample_member(
    db_session: AsyncSession,
    sample_vehicle_type: VehicleType,
    sample_member_group: MemberGroup,
) -> Member:
    member = Member(
        card_number="1234567890",
        name="John Doe",
        phone="08123456789",
        plate_number="B1234ABC",
        vehicle_type_id=sample_vehicle_type.id,
        member_group_id=sample_member_group.id,
        valid_from=date(2026, 1, 1),
        valid_until=date(2026, 12, 31),
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member


class TestListMembers:
    async def test_list_empty(self, client: AsyncClient):
        response = await client.get("/api/members")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_with_items(self, client: AsyncClient, sample_member: Member):
        response = await client.get("/api/members")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "John Doe"
        assert data[0]["card_number"] == "1234567890"

    async def test_list_search(self, client: AsyncClient, sample_member: Member):
        response = await client.get("/api/members?q=John")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        response = await client.get("/api/members?q=NONEXISTENT")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestCreateMember:
    async def test_create_success(
        self,
        client: AsyncClient,
        sample_vehicle_type: VehicleType,
        sample_member_group: MemberGroup,
    ):
        response = await client.post("/api/members", json={
            "card_number": "0987654321",
            "name": "Jane Doe",
            "phone": "08987654321",
            "plate_number": "B5678DEF",
            "vehicle_type_id": sample_vehicle_type.id,
            "member_group_id": sample_member_group.id,
            "valid_from": "2026-01-01",
            "valid_until": "2026-12-31",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Jane Doe"
        assert data["card_number"] == "0987654321"
        assert data["vehicle_type_name"] == "Motor"
        assert data["member_group_name"] == "Regular"

    async def test_create_validation_error(self, client: AsyncClient):
        response = await client.post("/api/members", json={"name": ""})
        assert response.status_code == 422


class TestGetMember:
    async def test_get_by_id(self, client: AsyncClient, sample_member: Member):
        response = await client.get(f"/api/members/{sample_member.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_member.id
        assert data["name"] == "John Doe"

    async def test_get_not_found(self, client: AsyncClient):
        response = await client.get("/api/members/99999")
        assert response.status_code == 404


class TestUpdateMember:
    async def test_update_success(self, client: AsyncClient, sample_member: Member):
        response = await client.patch(f"/api/members/{sample_member.id}", json={
            "name": "John Updated",
            "phone": "08111111111",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John Updated"
        assert data["phone"] == "08111111111"
        assert data["card_number"] == "1234567890"

    async def test_update_not_found(self, client: AsyncClient):
        response = await client.patch("/api/members/99999", json={"name": "X"})
        assert response.status_code == 404


class TestDeleteMember:
    async def test_delete_success(self, client: AsyncClient, sample_member: Member):
        response = await client.delete(f"/api/members/{sample_member.id}")
        assert response.status_code == 200

        response = await client.get(f"/api/members/{sample_member.id}")
        assert response.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient):
        response = await client.delete("/api/members/99999")
        assert response.status_code == 404
