"""Security headers middleware for FastAPI.

Adds defense-in-depth security headers to all HTTP responses.
Complements nginx-level headers with application-level enforcement.
"""

from collections.abc import Callable

from fastapi import Request, Response

DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "connect-src 'self' ws: wss:; "
    "font-src 'self' https://fonts.gstatic.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)


def create_security_headers_middleware(
    *,
    csp: str | None = None,
    enable_hsts: bool = False,
) -> Callable:
    """Factory returning plain async middleware function."""

    _csp = csp or DEFAULT_CSP
    _hsts_header = "max-age=31536000; includeSubDomains; preload"

    async def _middleware(request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        h = response.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Content-Security-Policy"] = _csp
        h["Referrer-Policy"] = "strict-origin-when-cross-origin"
        h["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )
        if enable_hsts:
            h["Strict-Transport-Security"] = _hsts_header
        return response

    return _middleware
