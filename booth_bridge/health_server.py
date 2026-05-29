"""Local HTTP /health endpoint for booth_bridge.

Bound to 127.0.0.1:5679. Returns a JSON snapshot of the bridge's runtime
state so ``parking-doctor``, the tray indicator, and any monitoring tool on
the booth PC can probe without speaking the WebSocket protocol.

This server speaks a deliberately tiny subset of HTTP/1.1 — only ``GET
/health`` is handled, everything else returns 404. Implementing on top of
``asyncio.start_server`` avoids dragging aiohttp/starlette into the bridge.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

from shared.logging import get_logger

logger = get_logger("booth_health")

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 5679
_MAX_REQUEST_BYTES = 4096


class HealthServer:
    """Tiny localhost HTTP server exposing /health for monitoring.

    ``snapshot_fn`` is called per-request and must return a JSON-serialisable
    dict. Keeping the snapshot pluggable means the server owns no domain
    state — main.py wires references at construction time.
    """

    def __init__(
        self,
        snapshot_fn: Callable[[], dict],
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
    ) -> None:
        self._snapshot_fn = snapshot_fn
        self._host = host
        self._port = port
        self._server: asyncio.base_events.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle, self._host, self._port
        )
        logger.info("health_server_started", host=self._host, port=self._port)

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        logger.info("health_server_stopped")

    async def serve_forever(self) -> None:
        """Block until the server is closed. Used by the supervisor wrapper."""
        if self._server is None:
            raise RuntimeError("HealthServer.start() must be called before serve_forever")
        await self._server.serve_forever()

    async def _handle(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            # Read at most _MAX_REQUEST_BYTES then stop. We don't care about
            # headers or body — only the request line. readuntil prevents a
            # slow-loris from holding the connection forever.
            try:
                request_line = await asyncio.wait_for(
                    reader.readuntil(b"\r\n"), timeout=2.0
                )
            except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                await self._write_response(writer, 400, "Bad Request", b"")
                return
            # Drain remaining headers but bound the read so we don't sit on
            # an attacker's open socket indefinitely.
            try:
                await asyncio.wait_for(
                    reader.readuntil(b"\r\n\r\n"), timeout=1.0
                )
            except (asyncio.IncompleteReadError, asyncio.TimeoutError):
                # Headers absent or truncated — still answer if request line OK.
                pass

            try:
                method, path, _ = request_line.decode("ascii", errors="replace").split(" ", 2)
            except ValueError:
                await self._write_response(writer, 400, "Bad Request", b"")
                return

            if method != "GET":
                await self._write_response(writer, 405, "Method Not Allowed", b"")
                return
            if path.split("?", 1)[0] != "/health":
                await self._write_response(writer, 404, "Not Found", b"")
                return

            try:
                snapshot = self._snapshot_fn()
            except Exception as e:
                logger.exception("health_snapshot_failed", error=str(e))
                body = json.dumps({"status": "error", "error": "snapshot_failed"}).encode()
                await self._write_response(writer, 500, "Internal Server Error", body)
                return

            body = json.dumps(snapshot, default=str).encode()
            await self._write_response(writer, 200, "OK", body)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    @staticmethod
    async def _write_response(
        writer: asyncio.StreamWriter,
        code: int,
        reason: str,
        body: bytes,
    ) -> None:
        head = (
            f"HTTP/1.1 {code} {reason}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode("ascii")
        try:
            writer.write(head + body)
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            pass
