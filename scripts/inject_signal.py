"""Inject Compass RSS signal into a running daemon via Redis Streams.

Bypasses the controller — useful for local testing without loop sensors.
The daemon's `handle_command(inject_rss)` calls `_dispatch_rss_message(frame)`
with `frame = 0xA6 + signal_bytes + 0xA9`.

Usage:
    python -m scripts.inject_signal --gate-id GIN01 --signal IN1ON
    python -m scripts.inject_signal --gate-id GIN01 --signal IN2ON   # ticket button
    python -m scripts.inject_signal --gate-id GOUT01 --signal IN1ON
    python -m scripts.inject_signal --gate-id GOUT01 --signal IN1OFF
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from shared.redis import RedisClient


async def _inject(gate_id: str, signal: str) -> None:
    client = RedisClient()
    await client.connect()
    stream = f"parking.commands.{gate_id}"
    msg_id = await client.xadd(
        stream,
        {"command_type": "inject_rss", "signal": signal},
    )
    print(f"injected signal={signal!r} into {stream} id={msg_id}")
    await client.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject RSS signal into running gate daemon")
    parser.add_argument("--gate-id", required=True, help="Gate code (e.g. GIN01, GOUT01)")
    parser.add_argument(
        "--signal",
        required=True,
        help="RSS signal text (IN1ON, IN1OFF, IN2ON, IN3ON, IN3OFF, IN4ON)",
    )
    args = parser.parse_args()
    asyncio.run(_inject(args.gate_id, args.signal))
    return 0


if __name__ == "__main__":
    sys.exit(main())
