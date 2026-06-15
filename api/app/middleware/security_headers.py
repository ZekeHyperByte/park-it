"""Security headers middleware for FastAPI.

Adds defense-in-depth security headers to all HTTP responses.
Complements nginx-level headers with application-level enforcement.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from shared.logging import get_logger

logger = get_logger("security_headers")

# Default Content Security Policy for the parking system
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses.

    Headers added:
        - X-Content-Type-Options: nosniff
        - X-Frame-Options: DENY
        - Content-Security-Policy: default CSP
        - Referrer-Policy: strict-origin-when-cross-origin
        - Permissions-Policy: restrict sensitive APIs
        - Strict-Transport-Security: HSTS (when HTTPS is enabled)
    """

    def __init__(
        self,
        app,
        csp: str | None = None,
        enable_hsts: bool = False,
    ):
        super().__init__(app)
        self.csp = csp or DEFAULT_CSP
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.csp

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (restrict sensitive browser APIs)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # HSTS (only when explicitly enabled / behind HTTPS)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
