"""Tests for gate control routes (manual open/close)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.main import app
from api.app.models import Gate
from api.database import get_db


def _unique_code(prefix: str) -> str:
    """Generate a unique gate code to avoid DB constraint collisions."""
    return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Create a test client with DB override and mock auth."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    from api.app.middleware import auth as auth_module
    original_require_operator = auth_module.require_operator
    original_get_current_user = auth_module.get_current_user

    async def mock_auth(request):
        return {"sub": "1", "username": "operator", "role": "operator"}

    auth_module.require_operator = mock_auth
    auth_module.get_current_user = mock_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    auth_module.require_operator = original_require_operator
    auth_module.get_current_user = original_get_current_user


@pytest.mark.asyncio
class TestGateControl:
    async def test_open_gate_success(self, client: AsyncClient, db_session: AsyncSession):
        """Should send open_gate command for active gate."""
        code = _unique_code("TG")
        gate = Gate(name="Test Gate", code=code, direction="IN", is_active=True)
        db_session.add(gate)
        await db_session.commit()
        await db_session.refresh(gate)

        with patch("api.app.routes.gates_unified.publish_command", new_callable=AsyncMock) as mock_pub:
            mock_pub.return_value = "mock-msg-id-001"
            resp = await client.post(
                f"/api/gates/{gate.id}/open",
                json={"reason": "operator"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["gate_id"] == code
        assert data["message"] == "Gate open command sent"

        mock_pub.assert_awaited_once()
        cmd = mock_pub.call_args[0][0]
        assert cmd.command_type == "open_gate"
        assert cmd.gate_id == code
        assert cmd.reason == "operator"

    async def test_open_gate_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent gate."""
        resp = await client.post(
            "/api/gates/99999/open",
            json={"reason": "operator"},
        )
        assert resp.status_code == 404

    async def test_open_gate_inactive(self, client: AsyncClient, db_session: AsyncSession):
        """Should return 400 for inactive gate."""
        code = _unique_code("IG")
        gate = Gate(name="Inactive Gate", code=code, direction="IN", is_active=False)
        db_session.add(gate)
        await db_session.commit()
        await db_session.refresh(gate)

        resp = await client.post(
            f"/api/gates/{gate.id}/open",
            json={"reason": "operator"},
        )
        assert resp.status_code == 400
        assert "not active" in resp.json()["detail"].lower()

    async def test_close_gate_success(self, client: AsyncClient, db_session: AsyncSession):
        """Should send close_gate command for DUAL relay gate."""
        code = _unique_code("DG")
        gate = Gate(name="Dual Gate", code=code, direction="OUT", is_active=True, relay_mode="DUAL")
        db_session.add(gate)
        await db_session.commit()
        await db_session.refresh(gate)

        with patch("api.app.routes.gates_unified.publish_command", new_callable=AsyncMock) as mock_pub:
            mock_pub.return_value = "mock-msg-id-002"
            resp = await client.post(
                f"/api/gates/{gate.id}/close",
                json={"reason": "maintenance"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["gate_id"] == code

        mock_pub.assert_awaited_once()
        cmd = mock_pub.call_args[0][0]
        assert cmd.command_type == "close_gate"
        assert cmd.gate_id == code
        assert cmd.reason == "maintenance"

    async def test_close_gate_single_relay_rejected(self, client: AsyncClient, db_session: AsyncSession):
        """Should return 400 for SINGLE relay mode."""
        code = _unique_code("SG")
        gate = Gate(name="Single Gate", code=code, direction="IN", is_active=True, relay_mode="SINGLE")
        db_session.add(gate)
        await db_session.commit()
        await db_session.refresh(gate)

        resp = await client.post(
            f"/api/gates/{gate.id}/close",
            json={"reason": "operator"},
        )
        assert resp.status_code == 400
        assert "DUAL" in resp.json()["detail"]

    async def test_close_gate_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent gate."""
        resp = await client.post(
            "/api/gates/99999/close",
            json={"reason": "operator"},
        )
        assert resp.status_code == 404
