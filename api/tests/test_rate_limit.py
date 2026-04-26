"""Tests for rate limiting middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, Request, Response
from starlette.testclient import TestClient

from api.app.middleware.rate_limit import RateLimitMiddleware


@pytest.fixture
def rate_limit_app():
    """Create a minimal FastAPI app with rate limiting."""
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        limits={"/api/login": (2, 60), "/api/payments/": (5, 60)},
        fallback_limit=(10, 60),
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/login")
    async def login():
        return {"token": "test"}

    @app.get("/other")
    async def other():
        return {"data": "test"}

    return app


class TestRateLimitMiddleware:
    def test_exempt_path_not_rate_limited(self, rate_limit_app):
        """Health endpoint should not be rate limited."""
        client = TestClient(rate_limit_app)

        # Make many requests — should all succeed
        for _ in range(20):
            resp = client.get("/api/health")
            assert resp.status_code == 200

    def test_rate_limit_headers_present(self, rate_limit_app):
        """Response should include rate limit headers."""
        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=0)
        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        mock_client = AsyncMock()
        mock_client.client = mock_redis

        with patch(
            "api.app.middleware.rate_limit.redis_client",
            mock_client,
        ):
            client = TestClient(rate_limit_app)
            resp = client.post("/api/login")

        assert resp.status_code == 200
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Window" in resp.headers
        assert resp.headers["X-RateLimit-Limit"] == "2"

    def test_rate_limit_429_response(self, rate_limit_app):
        """Should return 429 when limit exceeded."""
        import time

        future_ts = time.time() + 30  # 30 seconds in the future

        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=5)  # Over limit
        mock_redis.zrange = AsyncMock(return_value=[[b"", future_ts]])

        mock_client = AsyncMock()
        mock_client.client = mock_redis

        with patch(
            "api.app.middleware.rate_limit.redis_client",
            mock_client,
        ):
            client = TestClient(rate_limit_app)
            resp = client.post("/api/login")

        assert resp.status_code == 429
        # Retry-After should be approximately future_ts + window - now ≈ 90s
        retry_after = int(resp.headers["Retry-After"])
        assert 85 <= retry_after <= 95
        assert "Too many requests" in resp.text

    def test_fallback_limit_for_unmatched_paths(self, rate_limit_app):
        """Paths without specific limits use fallback."""
        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=0)
        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        mock_client = AsyncMock()
        mock_client.client = mock_redis

        with patch(
            "api.app.middleware.rate_limit.redis_client",
            mock_client,
        ):
            client = TestClient(rate_limit_app)
            resp = client.get("/other")

        assert resp.status_code == 200
        assert resp.headers["X-RateLimit-Limit"] == "10"

    def test_client_ip_from_x_forwarded_for(self, rate_limit_app):
        """Should use X-Forwarded-For header for client IP."""
        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=0)
        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        mock_client = AsyncMock()
        mock_client.client = mock_redis

        with patch(
            "api.app.middleware.rate_limit.redis_client",
            mock_client,
        ):
            client = TestClient(rate_limit_app)
            resp = client.post(
                "/api/login",
                headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"},
            )

        assert resp.status_code == 200
        # Check Redis key includes the forwarded IP
        calls = mock_redis.zadd.call_args_list
        assert len(calls) > 0
        redis_key = calls[0][0][0]
        assert "1.2.3.4" in redis_key

    def test_redis_failure_fail_open(self, rate_limit_app):
        """If Redis fails, allow the request (fail open)."""
        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(side_effect=Exception("Redis down"))

        mock_client = AsyncMock()
        mock_client.client = mock_redis

        with patch(
            "api.app.middleware.rate_limit.redis_client",
            mock_client,
        ):
            client = TestClient(rate_limit_app)
            resp = client.post("/api/login")

        assert resp.status_code == 200
