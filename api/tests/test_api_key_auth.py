import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from api.app.middleware.api_key import require_api_key
from shared.config import get_settings

app = FastAPI()

@app.get("/internal/test")
async def _test_endpoint(api_key: bool = Depends(require_api_key)):
    return {"ok": True}

@pytest.mark.anyio
async def test_api_key_missing(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "test-key-123")
    get_settings.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/test")
        assert resp.status_code == 403

@pytest.mark.anyio
async def test_api_key_invalid(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "test-key-123")
    get_settings.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/test", headers={"X-API-Key": "bad-key"})
        assert resp.status_code == 403

@pytest.mark.anyio
async def test_api_key_valid(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "test-key-123")
    get_settings.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/test", headers={"X-API-Key": "test-key-123"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

@pytest.mark.anyio
async def test_api_key_unconfigured(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    get_settings.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/test", headers={"X-API-Key": "any-key"})
        assert resp.status_code == 403
