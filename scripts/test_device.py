#!/usr/bin/env python3
"""Probe a serial port, TCP endpoint, or ping target for the setup wizard.

Emits a single JSON line on stdout. Always exits 0 — the JSON's `ok` field
reflects success/failure. Errors during exec (bad args, missing pyserial)
exit non-zero and the wrapper falls back to that message.

Usage:
    python scripts/test_device.py serial --device /dev/parking-gate --baudrate 9600
    python scripts/test_device.py tcp    --host 192.168.1.100 --port 5000
    python scripts/test_device.py ping   --host 192.168.1.50
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from typing import Any


def _result(ok: bool, latency_ms: float | None = None, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": ok}
    if latency_ms is not None:
        out["latency_ms"] = round(latency_ms, 2)
    out.update(extra)
    return out


def probe_serial(device: str, baudrate: int) -> dict[str, Any]:
    try:
        import serial  # type: ignore[import-not-found]
    except ImportError:
        return _result(False, error="pyserial not installed on server")

    start = time.perf_counter()
    try:
        port = serial.Serial(
            device,
            baudrate=baudrate,
            timeout=1.0,
            write_timeout=1.0,
        )
    except FileNotFoundError:
        return _result(False, error=f"no such device: {device}")
    except PermissionError:
        return _result(
            False,
            error=f"permission denied opening {device} — add user to 'dialout' group",
        )
    except serial.SerialException as exc:  # type: ignore[attr-defined]
        return _result(False, error=str(exc))

    try:
        # Drain whatever was buffered; many gates send a banner on connect.
        port.reset_input_buffer()
        time.sleep(0.05)
        pending = port.in_waiting if hasattr(port, "in_waiting") else 0
        detail = "Port opened"
        if pending:
            detail = f"Port opened, {pending} byte(s) waiting"
    finally:
        port.close()

    return _result(True, latency_ms=(time.perf_counter() - start) * 1000.0, detail=detail)


def probe_tcp(host: str, port: int, timeout: float = 3.0) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except socket.gaierror as exc:
        return _result(False, error=f"dns lookup failed: {exc}")
    except socket.timeout:
        return _result(False, error=f"connection timed out after {timeout:.1f}s")
    except ConnectionRefusedError:
        return _result(False, error="connection refused (service not listening)")
    except OSError as exc:
        return _result(False, error=str(exc))

    return _result(True, latency_ms=(time.perf_counter() - start) * 1000.0, detail="tcp ok")


def probe_ping(host: str, timeout_s: float = 2.0) -> dict[str, Any]:
    cmd = ["ping", "-c", "1", "-W", str(int(timeout_s)), host]
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s + 1,
        )
    except FileNotFoundError:
        return _result(False, error="ping binary not present")
    except subprocess.TimeoutExpired:
        return _result(False, error=f"ping timed out after {timeout_s:.1f}s")

    if proc.returncode != 0:
        return _result(False, error=proc.stdout.strip() or "ping unreachable")
    return _result(True, latency_ms=(time.perf_counter() - start) * 1000.0, detail="ping ok")


def main() -> int:
    parser = argparse.ArgumentParser(description="Device probe for setup wizard")
    subs = parser.add_subparsers(dest="kind", required=True)

    s = subs.add_parser("serial")
    s.add_argument("--device", required=True)
    s.add_argument("--baudrate", type=int, default=9600)

    t = subs.add_parser("tcp")
    t.add_argument("--host", required=True)
    t.add_argument("--port", type=int, required=True)
    t.add_argument("--timeout", type=float, default=3.0)

    p = subs.add_parser("ping")
    p.add_argument("--host", required=True)
    p.add_argument("--timeout", type=float, default=2.0)

    args = parser.parse_args()
    if args.kind == "serial":
        result = probe_serial(args.device, args.baudrate)
    elif args.kind == "tcp":
        result = probe_tcp(args.host, args.port, args.timeout)
    else:
        result = probe_ping(args.host, args.timeout)

    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
