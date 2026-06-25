"""Gate controller connectivity and protocol diagnostic.

Usage:
    python -m scripts.hardware.controller_diagnostic 192.168.1.100 5000
"""

import argparse
import socket
import sys
import time

from protocols.compass.parser import parse_stat
from protocols.compass.protocol import cmd_stat


def check_tcp_connect(host: str, port: int, timeout: float = 5.0) -> dict:
    """Test TCP connectivity to controller."""
    start = time.perf_counter()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        latency_ms = (time.perf_counter() - start) * 1000
        sock.close()
        return {
            "status": "ok",
            "host": host,
            "port": port,
            "latency_ms": round(latency_ms, 2),
        }
    except TimeoutError:
        return {"status": "timeout", "host": host, "port": port, "error": "Connection timed out"}
    except ConnectionRefusedError:
        return {"status": "refused", "host": host, "port": port, "error": "Connection refused"}
    except Exception as e:
        return {"status": "error", "host": host, "port": port, "error": str(e)}


def send_stat_command(host: str, port: int, timeout: float = 2.0) -> dict:
    """Send STAT command and parse response."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.settimeout(timeout)
        sock.sendall(cmd_stat())
        response = sock.recv(1024)
        sock.close()
        parsed = parse_stat(response)
        return {
            "status": "ok",
            "raw_hex": response.hex(),
            "parsed": parsed,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def run_full_diagnostic(host: str, port: int) -> dict:
    """Run complete controller diagnostic."""
    results = {
        "host": host,
        "port": port,
        "tcp_connect": check_tcp_connect(host, port),
    }
    if results["tcp_connect"]["status"] == "ok":
        results["stat_command"] = send_stat_command(host, port)
    return results


def main():
    parser = argparse.ArgumentParser(description="Gate Controller Diagnostic")
    parser.add_argument("host", help="Controller IP address")
    parser.add_argument("port", type=int, help="Controller port")
    args = parser.parse_args()

    results = run_full_diagnostic(args.host, args.port)
    print(results)
    sys.exit(0 if results["tcp_connect"]["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
