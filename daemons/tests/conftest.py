"""Pytest fixtures for daemon tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
import redis.asyncio as aioredis



class FakeRedis:
    """In-memory fake Redis for testing daemons without a real Redis server."""

    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.groups: dict[str, set[str]] = {}
        self.pubsub: dict[str, list[str]] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self._seq = 0
        self.closed = False

    def _next_id(self) -> str:
        self._seq += 1
        return f"{self._seq}-0"

    async def xgroup_create(
        self, stream: str, groupname: str, **kwargs: Any
    ) -> bytes:
        key = f"{stream}:{groupname}"
        if key in self.groups:
            raise aioredis.ResponseError("BUSYGROUP Consumer Group name already exists")
        self.groups[key] = set()
        if kwargs.get("mkstream") and stream not in self.streams:
            self.streams[stream] = []
        return b"OK"

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int = 1,
        block: int | None = 5000,
    ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
        result: list[tuple[str, list[tuple[str, dict[str, str]]]]] = []
        for stream, last_id in streams.items():
            key = f"{stream}:{groupname}"
            pending = self.streams.get(stream, [])
            entries: list[tuple[str, dict[str, str]]] = []
            for msg_id, fields in pending:
                if msg_id not in self.groups.get(key, set()):
                    entries.append((msg_id, fields))
                    self.groups[key].add(msg_id)
                    if len(entries) >= count:
                        break
            if entries:
                result.append((stream, entries))
        return result

    async def xack(self, stream: str, groupname: str, *ids: str) -> int:
        key = f"{stream}:{groupname}"
        acked = 0
        for msg_id in ids:
            if key in self.groups and msg_id in self.groups[key]:
                acked += 1
        return acked

    async def publish(self, channel: str, message: str) -> int:
        self.pubsub.setdefault(channel, []).append(message)
        return 0

    async def hset(self, name: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(name, {}).update(mapping)
        return len(mapping)

    async def hgetall(self, name: str) -> dict[str, str]:
        return dict(self.hashes.get(name, {}))

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_redis() -> FakeRedis:
    """Return a fresh FakeRedis instance."""
    return FakeRedis()


@pytest_asyncio.fixture
async def daemon_lifecycle() -> AsyncGenerator[Any, None]:
    """Provide helper for managing daemon lifecycle in tests."""
    active_daemons: list[Any] = []

    def register(daemon: Any) -> None:
        active_daemons.append(daemon)

    yield register

    for daemon in active_daemons:
        await daemon.stop()


@pytest.fixture
def gate_in_config() -> dict[str, Any]:
    """Sample gate-in configuration."""
    return {
        "id": 1,
        "name": "Gate In Utara",
        "code": "gate-in-1",
        "gate_mode": "CASH",
        "protocol": "compass",
        "controller_host": "192.168.1.10",
        "controller_port": 4001,
        "emoney_minimum_balance": 10000,
        "print_decision_timeout_seconds": 10,
        "has_close_sensor": False,
        "gate_close_duration_ms": 5000,
        "relay_mode": "SINGLE",
        "camera_url": "http://192.168.1.50/snapshot",
    }


@pytest.fixture
def gate_out_config() -> dict[str, Any]:
    """Sample gate-out configuration."""
    return {
        "id": 1,
        "name": "Gate Out Utara",
        "code": "gate-out-1",
        "protocol": "compass",
        "controller_host": "192.168.1.11",
        "controller_port": 4002,
        "payment_timeout_seconds": 120,
        "has_close_sensor": False,
        "gate_close_duration_ms": 5000,
        "relay_mode": "SINGLE",
        "emoney_reader_id": 1,
        "camera_url": "http://192.168.1.51/snapshot",
    }


class MockCompassTransport:
    """Mock Compass TCP transport for testing."""

    def __init__(self) -> None:
        self.sent_commands: list[bytes] = []
        self._responses: list[bytes] = []
        self._response_index = 0
        self._connected = False

    def connect(self, timeout: float = 5.0) -> None:
        self._connected = True

    def close(self) -> None:
        self._connected = False

    def send(self, command: bytes) -> None:
        self.sent_commands.append(command)

    def send_recv(self, command: bytes, timeout: float = 1.0) -> bytes:
        self.sent_commands.append(command)
        if self._response_index < len(self._responses):
            resp = self._responses[self._response_index]
            self._response_index += 1
            self._last_response = resp
            return resp
        # Repeat last response if available, otherwise empty
        return getattr(self, "_last_response", b"")

    def is_connected(self) -> bool:
        return self._connected

    def inject_response(self, response: bytes) -> None:
        self._responses.append(response)

    def inject_stat_in1_on(self) -> None:
        """Inject STAT response with IN1 ON."""
        self._responses.append(b"\xa6STAT10IN2OFF\xa9")

    def inject_stat_in2_on(self) -> None:
        """Inject STAT response with IN2 ON."""
        self._responses.append(b"\xa6STAT1IN1OFF\xa9")

    def inject_stat_wiegand_w(self, card_hex: str) -> None:
        """Inject STAT response with Wiegand W data."""
        resp = f"\xa6STAT1W{card_hex}\xa9".encode()
        self._responses.append(resp)

    def inject_stat_empty(self) -> None:
        """Inject empty STAT response."""
        self._responses.append(b"\xa6STAT0IN1OFFIN2OFF\xa9")

    def reset(self) -> None:
        self.sent_commands.clear()
        self._responses.clear()
        self._response_index = 0


@pytest.fixture
def mock_compass() -> MockCompassTransport:
    """Return a fresh MockCompassTransport (pre-connected)."""
    transport = MockCompassTransport()
    transport.connect()
    return transport


class MockPasstiTransport:
    """Mock PASSTI transport for testing."""

    def __init__(self) -> None:
        self.sent_frames: list[bytes] = []
        self._responses: list[dict[str, Any]] = []
        self._response_index = 0

    async def send_recv(self, frame: bytes, timeout: float = 10.0) -> dict[str, Any]:
        self.sent_frames.append(frame)
        if self._response_index < len(self._responses):
            resp = self._responses[self._response_index]
            self._response_index += 1
            return resp
        return {"ok": False, "error": "No mock response configured"}

    async def close(self) -> None:
        pass

    def inject_response(self, response: dict[str, Any]) -> None:
        self._responses.append(response)

    def inject_check_balance(self, card_number: str, balance: int) -> None:
        """Inject a successful Check Balance response."""
        card_type = 0x02  # Mandiri eMoney
        body = (
            bytes([card_type])
            + bytes.fromhex(card_number)
            + balance.to_bytes(4, "big")
        )
        self._responses.append({
            "ok": True,
            "resp_code": 0x00,
            "status": (0x00, 0x00, 0x00),
            "status_msg": "OK",
            "body": body,
        })

    def inject_deduct_success(
        self, card_number: str, deducted: int, remaining: int, trans_counter: int
    ) -> None:
        """Inject a successful Deduct response."""
        card_type = 0x02
        now_bcd = bytes([0x25, 0x04, 0x25, 0x10, 0x30, 0x00, 0x00])
        body = (
            bytes([card_type])
            + bytes.fromhex("1234567890ABCDEF")  # MID
            + bytes.fromhex("12345678")  # TID
            + now_bcd
            + bytes.fromhex(card_number)
            + deducted.to_bytes(4, "big")
            + remaining.to_bytes(4, "big")
            + trans_counter.to_bytes(4, "big")
        )
        self._responses.append({
            "ok": True,
            "resp_code": 0x00,
            "status": (0x00, 0x00, 0x00),
            "status_msg": "OK",
            "body": body,
        })

    def inject_insufficient_balance(self, card_number: str = "1234567890ABCDEF", balance: int = 5000) -> None:
        """Inject a Check Balance response with low balance (below typical threshold)."""
        card_type = 0x02  # Mandiri eMoney
        body = (
            bytes([card_type])
            + bytes.fromhex(card_number)
            + balance.to_bytes(4, "big")
        )
        self._responses.append({
            "ok": True,
            "resp_code": 0x00,
            "status": (0x00, 0x00, 0x00),
            "status_msg": "OK",
            "body": body,
        })

    def inject_lost_contact(self) -> None:
        """Inject lost contact error."""
        self._responses.append({
            "ok": False,
            "resp_code": 0x00,
            "status": (0x01, 0x10, 0x05),
            "status_msg": "Lost contact",
            "body": b"",
        })

    def reset(self) -> None:
        self.sent_frames.clear()
        self._responses.clear()
        self._response_index = 0


@pytest.fixture
def mock_passti() -> MockPasstiTransport:
    """Return a fresh MockPasstiTransport."""
    return MockPasstiTransport()
