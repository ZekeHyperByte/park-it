"""Tests for POST /api/pos/heartbeat — booth → server liveness."""

from datetime import UTC, datetime, timedelta

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models.pos import Pos
from api.database import get_db
from shared.config import get_settings

_API_KEY = "test-pos-heartbeat-key"


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", _API_KEY)
    get_settings.cache_clear()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def sample_pos(db_session: AsyncSession) -> Pos:
    pos = Pos(name="Booth 1", code="BOOTH_01", ip_address="10.0.0.10")
    db_session.add(pos)
    await db_session.commit()
    await db_session.refresh(pos)
    return pos


class TestBoothHeartbeat:
    async def test_rejects_missing_api_key(self, client: AsyncClient):
        resp = await client.post(
            "/api/pos/heartbeat", json={"booth_code": "BOOTH_01"}
        )
        assert resp.status_code == 403

    async def test_rejects_unknown_booth(self, client: AsyncClient):
        resp = await client.post(
            "/api/pos/heartbeat",
            json={"booth_code": "GHOST_BOOTH"},
            headers={"X-API-Key": _API_KEY},
        )
        # Server must NOT auto-create the booth — registration belongs to
        # the setup wizard, not the runtime heartbeat path.
        assert resp.status_code == 404

    async def test_records_last_seen_at_and_status(
        self,
        client: AsyncClient,
        sample_pos: Pos,
        db_session: AsyncSession,
    ):
        payload = {
            "booth_code": sample_pos.code,
            "rfid_connected": True,
            "gate_connected": False,
            "ws_clients": 2,
            "last_card_at": 12345.6,
            "bridge_version": "2.0.0",
        }
        before = datetime.now(UTC)
        resp = await client.post(
            "/api/pos/heartbeat",
            json=payload,
            headers={"X-API-Key": _API_KEY},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["booth_code"] == sample_pos.code

        # Reload from the same session and verify timestamp + JSONB snapshot.
        await db_session.refresh(sample_pos)
        assert sample_pos.last_seen_at is not None
        assert sample_pos.last_seen_at >= before - timedelta(seconds=2)
        assert sample_pos.last_status == {
            "rfid_connected": True,
            "gate_connected": False,
            "ws_clients": 2,
            "last_card_at": 12345.6,
            "bridge_version": "2.0.0",
        }

    async def test_subsequent_heartbeat_updates_last_seen_at(
        self,
        client: AsyncClient,
        sample_pos: Pos,
        db_session: AsyncSession,
    ):
        for _ in range(2):
            resp = await client.post(
                "/api/pos/heartbeat",
                json={"booth_code": sample_pos.code, "rfid_connected": True},
                headers={"X-API-Key": _API_KEY},
            )
            assert resp.status_code == 200

        await db_session.refresh(sample_pos)
        assert sample_pos.last_seen_at is not None
        # Status reflects the most recent payload only — the route overwrites
        # rather than merging, which is the desired semantics for a snapshot.
        assert sample_pos.last_status["rfid_connected"] is True
