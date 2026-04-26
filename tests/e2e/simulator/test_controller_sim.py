import pytest
import asyncio

from tests.e2e.simulator.controller_sim import CompassControllerSimulator


class TestCompassControllerSimulator:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        sim = CompassControllerSimulator(host="127.0.0.1", port=0)
        await sim.start()
        assert sim.port > 0
        await sim.stop()

    @pytest.mark.asyncio
    async def test_stat_response(self):
        sim = CompassControllerSimulator(host="127.0.0.1", port=0)
        await sim.start()

        reader, writer = await asyncio.open_connection("127.0.0.1", sim.port)
        writer.write(b"\xa6STAT\xa9")
        await writer.drain()

        data = await asyncio.wait_for(reader.read(1024), timeout=2.0)
        writer.close()
        await writer.wait_closed()
        await sim.stop()

        assert b"IN1OFF" in data
