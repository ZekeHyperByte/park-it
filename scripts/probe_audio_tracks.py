"""Probe controller audio tracks one-by-one to map track number -> sound.

Usage:
    python scripts/probe_audio_tracks.py GIN-01            # play tracks 1..20, 3s apart
    python scripts/probe_audio_tracks.py GIN-01 7          # play single track 7
    python scripts/probe_audio_tracks.py GIN-01 1 15 4     # tracks 1..15, 4s apart

Requires the gate_in daemon for the gate to be running and connected to the
controller. This only publishes the play_audio command onto the Redis Stream;
the daemon translates it to the MT controller command.
"""

import asyncio
import sys

from api.app.services.gate_command import publish_command
from shared.events import PlayAudioCommand


async def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    gate_id = args[0]

    if len(args) == 2:
        track = int(args[1])
        print(f"[{gate_id}] play track {track}")
        await publish_command(PlayAudioCommand(gate_id=gate_id, track=track))
        return

    start = int(args[1]) if len(args) > 1 else 1
    end = int(args[2]) if len(args) > 2 else 20
    delay = float(args[3]) if len(args) > 3 else 3.0

    for track in range(start, end + 1):
        print(f"[{gate_id}] play track {track} ... (next in {delay}s)")
        await publish_command(PlayAudioCommand(gate_id=gate_id, track=track))
        await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
