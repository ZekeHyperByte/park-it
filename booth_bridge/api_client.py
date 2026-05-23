"""HTTP client for booth_bridge to call API.

Handles gate config fetch + booth-authenticated payment endpoints.
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.request
from typing import Any

from shared.logging import get_logger

logger = get_logger("booth_api_client")

# Retry only on connection-level failures where the request almost certainly
# never reached the server. A bare socket/connection error (refused, DNS, reset
# before send) is safe to retry; a timeout is NOT — the server may have already
# processed it, and re-POSTing a payment could double-process.
_RETRYABLE = (ConnectionError, urllib.error.URLError)
_MAX_ATTEMPTS = 3
_BACKOFF_S = 0.5


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.URLError):
        # Timeouts surface as URLError(reason=timeout) — do not retry those.
        reason = getattr(exc, "reason", None)
        if isinstance(reason, TimeoutError) or isinstance(exc, urllib.error.HTTPError):
            return False
        return isinstance(reason, (ConnectionError, OSError))
    return isinstance(exc, ConnectionError)


class ApiClient:
    """Thin async HTTP client using urllib via threads (avoids extra deps)."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_sync, path, body)

    async def _get(self, path: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_sync, path)

    def _get_sync(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        # GET is idempotent — retry freely on any transient error incl. timeout.
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                req = urllib.request.Request(
                    url, headers={"X-API-Key": self.api_key}, method="GET"
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode())
            except _RETRYABLE as e:
                last_exc = e
                if attempt < _MAX_ATTEMPTS:
                    logger.warning("api_get_retry", path=path, attempt=attempt, error=str(e))
                    time.sleep(_BACKOFF_S * attempt)
        raise last_exc  # type: ignore[misc]

    def _post_sync(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode()
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": self.api_key,
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read().decode())
            except Exception as e:
                last_exc = e
                # Only retry POST when the request never reached the server.
                if attempt < _MAX_ATTEMPTS and _is_retryable(e):
                    logger.warning("api_post_retry", path=path, attempt=attempt, error=str(e))
                    time.sleep(_BACKOFF_S * attempt)
                else:
                    raise
        raise last_exc  # type: ignore[misc]

    async def fetch_gate(self, gate_code: str) -> dict[str, Any] | None:
        try:
            return await self._get(f"/api/gates/by-code/{gate_code}")
        except Exception as e:
            logger.error("fetch_gate_failed", gate_code=gate_code, error=str(e))
            return None

    async def rfid_exit(self, gate_id: str, gate_out_id: int, card_number: str) -> dict[str, Any]:
        try:
            return await self._post(
                "/api/payments/rfid/booth",
                {"gate_id": gate_id, "gate_out_id": gate_out_id, "card_number": card_number},
            )
        except Exception as e:
            logger.error("rfid_exit_failed", card=card_number, error=str(e))
            return {"success": False, "message": str(e)}
