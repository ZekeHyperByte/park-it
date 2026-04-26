"""Tests for Prometheus metrics endpoint and instrumentation."""

import pytest
from httpx import ASGITransport, AsyncClient

from api.app.main import app
from api.app.middleware.metrics import (
    get_metrics_response,
    http_requests_total,
    payment_attempts_total,
    payment_success_total,
)


@pytest.mark.asyncio
async def test_metrics_endpoint_exists():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "python_info" in response.text or "# HELP" in response.text


@pytest.mark.asyncio
async def test_metrics_middleware_records_request():
    """Verify that calling an endpoint increments the request counter."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Reset counter for this test path to avoid flakiness from other tests
        before = http_requests_total.labels(
            method="GET", endpoint="/api/health", status_code="200"
        )._value.get()

        response = await client.get("/api/health")
        assert response.status_code == 200

        after = http_requests_total.labels(
            method="GET", endpoint="/api/health", status_code="200"
        )._value.get()
        assert after >= before + 1


@pytest.mark.asyncio
async def test_metrics_response_format():
    response = get_metrics_response()
    assert response.status_code == 200
    assert "prometheus" in response.media_type or "plain" in response.media_type


class TestPaymentCounters:
    def test_payment_attempts_counter_exists(self):
        # Ensure we can increment without error
        payment_attempts_total.labels(method="cash").inc()
        payment_attempts_total.labels(method="rfid").inc()
        payment_attempts_total.labels(method="emoney").inc()

    def test_payment_success_counter_exists(self):
        payment_success_total.labels(method="cash").inc()
        payment_success_total.labels(method="rfid").inc()
        payment_success_total.labels(method="emoney").inc()
