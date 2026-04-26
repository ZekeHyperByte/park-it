"""Prometheus metrics middleware and endpoint."""

import time

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Business metrics
payment_attempts_total = Counter(
    "payment_attempts_total",
    "Total payment attempts",
    ["method"],  # cash, rfid, emoney
)

payment_success_total = Counter(
    "payment_success_total",
    "Total successful payments",
    ["method"],
)

settlement_files_generated_total = Counter(
    "settlement_files_generated_total",
    "Total settlement files generated",
)


def get_metrics_response() -> Response:
    """Return Prometheus metrics as HTTP response."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


async def metrics_middleware(request: Request, call_next):
    """Record request metrics."""
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    path = request.url.path
    method = request.method
    status = str(response.status_code)

    # Skip metrics endpoint itself
    if path == "/metrics":
        return response

    http_requests_total.labels(method=method, endpoint=path, status_code=status).inc()
    http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)

    return response
