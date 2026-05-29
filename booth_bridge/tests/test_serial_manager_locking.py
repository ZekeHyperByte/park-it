"""Tests for booth_bridge.serial_manager per-peripheral locking.

Ensures concurrent ``send`` calls on the same peripheral are serialised, so
two callers can't interleave reset/write/read sequences on the same wire.
Different peripherals must remain independent (no global lock contention).
"""

from __future__ import annotations

import threading
import time

import pytest

from booth_bridge.serial_manager import SerialManager


class _FakeSerial:
    """Minimal pyserial stand-in that records ordered events from callers."""

    def __init__(self, events: list[tuple[str, str, float]], peripheral: str) -> None:
        self.events = events
        self.peripheral = peripheral
        self.is_open = True

    def reset_input_buffer(self) -> None:  # pragma: no cover - trivial
        self.events.append((self.peripheral, "reset", time.monotonic()))
        time.sleep(0.02)

    def write(self, data: bytes) -> int:
        self.events.append((self.peripheral, f"write:{data.decode()}", time.monotonic()))
        time.sleep(0.02)
        return len(data)

    def read(self, n: int) -> bytes:
        self.events.append((self.peripheral, "read", time.monotonic()))
        time.sleep(0.02)
        return b""

    def close(self) -> None:
        self.is_open = False


@pytest.fixture
def manager_with_fakes() -> SerialManager:
    mgr = SerialManager(
        {
            "emoney_reader": {"enabled": True, "device": "/dev/null", "baudrate": 38400},
            "receipt_printer": {"enabled": True, "device": "/dev/null", "baudrate": 9600},
        }
    )
    events: list[tuple[str, str, float]] = []
    mgr._connections["emoney_reader"] = _FakeSerial(events, "emoney_reader")  # type: ignore[assignment]
    mgr._connections["receipt_printer"] = _FakeSerial(events, "receipt_printer")  # type: ignore[assignment]
    mgr._events = events  # type: ignore[attr-defined]
    return mgr


def _run_send(mgr: SerialManager, peripheral: str, payload: bytes) -> None:
    mgr.send(peripheral, payload)


def test_same_peripheral_calls_serialised(manager_with_fakes: SerialManager) -> None:
    """Two concurrent send() on the same peripheral must not interleave."""
    mgr = manager_with_fakes
    events: list[tuple[str, str, float]] = mgr._events  # type: ignore[attr-defined]

    t1 = threading.Thread(target=_run_send, args=(mgr, "emoney_reader", b"AAA"))
    t2 = threading.Thread(target=_run_send, args=(mgr, "emoney_reader", b"BBB"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Each send produces exactly 3 events (reset, write, read). Expect two
    # complete runs back-to-back, never an A-then-B-then-A interleave.
    for_emoney = [e for e in events if e[0] == "emoney_reader"]
    assert len(for_emoney) == 6
    first_writes = [i for i, e in enumerate(for_emoney) if e[1].startswith("write:")]
    assert len(first_writes) == 2
    # The first run's read (index after first write +1) must come before the
    # second run's reset.
    first_run_end = first_writes[0] + 2  # write, read
    second_run_start = first_writes[1] - 1  # reset before second write
    assert first_run_end < second_run_start or first_run_end == second_run_start - 0
    # Equivalent assertion: the second run's reset is strictly after the
    # first run's read.
    first_read_idx = first_writes[0] + 1
    second_reset_idx = first_writes[1] - 1
    assert for_emoney[first_read_idx][1] == "read"
    assert for_emoney[second_reset_idx][1] == "reset"
    assert second_reset_idx > first_read_idx


def test_different_peripherals_run_concurrently(manager_with_fakes: SerialManager) -> None:
    """Locks must be per-peripheral, not global, so different ports don't block."""
    mgr = manager_with_fakes
    events: list[tuple[str, str, float]] = mgr._events  # type: ignore[attr-defined]

    start_barrier = threading.Barrier(2)

    def _send(peripheral: str, payload: bytes) -> None:
        start_barrier.wait()
        mgr.send(peripheral, payload)

    t1 = threading.Thread(target=_send, args=("emoney_reader", b"AAA"))
    t2 = threading.Thread(target=_send, args=("receipt_printer", b"BBB"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # If locks were global, all emoney events would precede all printer events
    # (or vice versa). With per-peripheral locks they may interleave; assert
    # that at least one printer event appears before all emoney events finish.
    emoney_indices = [i for i, e in enumerate(events) if e[0] == "emoney_reader"]
    printer_indices = [i for i, e in enumerate(events) if e[0] == "receipt_printer"]
    assert emoney_indices, "expected emoney events"
    assert printer_indices, "expected printer events"
    assert min(printer_indices) < max(emoney_indices)
