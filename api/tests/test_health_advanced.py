"""Tests for advanced health check endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from api.app.main import app


@pytest.mark.asyncio
async def test_health_basic():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "parking-api"
        assert "checks" not in data


@pytest.mark.asyncio
async def test_health_detailed():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health?detailed=true")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "degraded")
        assert data["service"] == "parking-api"
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
        assert data["checks"]["database"]["status"] in ("ok", "error")
        assert data["checks"]["redis"]["status"] in ("ok", "error")
