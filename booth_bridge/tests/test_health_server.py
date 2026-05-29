"""Tests for booth_bridge.health_server."""

from __future__ import annotations

import asyncio
import json
import socket

import pytest

from booth_bridge.health_server import HealthServer


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def _http_get(host: str, port: int, path: str = "/health") -> tuple[int, dict]:
    reader, writer = await asyncio.open_connection(host, port)
    writer.write(
        f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode()
    )
    await writer.drain()
    raw = await reader.read()
    writer.close()
    await writer.wait_closed()
    head, _, body = raw.partition(b"\r\n\r\n")
    status_line = head.split(b"\r\n", 1)[0].decode("ascii")
    code = int(status_line.split(" ", 2)[1])
    payload: dict = {}
    if body:
        try:
            payload = json.loads(body.decode("utf-8"))
        except ValueError:
            payload = {}
    return code, payload


@pytest.mark.asyncio
async def test_health_returns_snapshot() -> None:
    snapshot = {"status": "ok", "rfid": {"connected": True}}
    server = HealthServer(lambda: snapshot, port=_free_port())
    await server.start()
    try:
        code, body = await _http_get("127.0.0.1", server._port)
        assert code == 200
        assert body == snapshot
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_unknown_path_returns_404() -> None:
    server = HealthServer(lambda: {"status": "ok"}, port=_free_port())
    await server.start()
    try:
        code, _ = await _http_get("127.0.0.1", server._port, "/other")
        assert code == 404
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_method_other_than_get_rejected() -> None:
    server = HealthServer(lambda: {"status": "ok"}, port=_free_port())
    await server.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", server._port)
        writer.write(b"POST /health HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        await writer.drain()
        raw = await reader.read()
        writer.close()
        await writer.wait_closed()
        assert b"405" in raw.split(b"\r\n", 1)[0]
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_snapshot_exception_returns_500() -> None:
    def boom() -> dict:
        raise RuntimeError("snapshot boom")

    server = HealthServer(boom, port=_free_port())
    await server.start()
    try:
        code, body = await _http_get("127.0.0.1", server._port)
        assert code == 500
        assert body["status"] == "error"
    finally:
        await server.stop()
