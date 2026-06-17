"""Tests for security headers middleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.middleware.security_headers import create_security_headers_middleware


@pytest.fixture
def client():
    app = FastAPI()
    app.middleware("http")(create_security_headers_middleware())

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    return TestClient(app)


class TestSecurityHeadersMiddleware:
    """Test suite for security headers middleware."""

    def test_x_content_type_options(self, client):
        response = client.get("/test")
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self, client):
        response = client.get("/test")
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_content_security_policy(self, client):
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_referrer_policy(self, client):
        response = client.get("/test")
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client):
        response = client.get("/test")
        pp = response.headers["Permissions-Policy"]
        assert "camera=()" in pp
        assert "microphone=()" in pp

    def test_hsts_disabled_by_default(self, client):
        response = client.get("/test")
        assert "Strict-Transport-Security" not in response.headers

    def test_hsts_when_enabled(self):
        app = FastAPI()
        app.middleware("http")(create_security_headers_middleware(enable_hsts=True))

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

    def test_custom_csp(self):
        app = FastAPI()
        app.middleware("http")(create_security_headers_middleware(csp="default-src 'none';"))

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")
        assert response.headers["Content-Security-Policy"] == "default-src 'none';"

    def test_response_body_unchanged(self, client):
        response = client.get("/test")
        assert response.json() == {"status": "ok"}

    def test_health_endpoint_has_headers(self, client):
        """Security headers should be present even on public health endpoints."""
        response = client.get("/test")
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
