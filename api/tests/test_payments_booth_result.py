import pytest
from httpx import ASGITransport, AsyncClient
from api.app.main import app
from shared.config import get_settings


@pytest.mark.anyio
async def test_emoney_booth_result_auth_required():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/payments/emoney/booth-result", json={})
        assert resp.status_code == 403


@pytest.mark.anyio
async def test_emoney_booth_result_invalid_card(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "booth-key")
    get_settings.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/payments/emoney/booth-result",
            headers={"X-API-Key": "booth-key"},
            json={
                "gate_id": "GOUT01",
                "gate_out_id": 1,
                "card_number": "NONEXISTENT",
                "status": "SUCCESS",
                "deduct_amount": 5000,
                "balance_before": 100000,
                "balance_after": 95000,
                "transaction_counter": 1,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False
