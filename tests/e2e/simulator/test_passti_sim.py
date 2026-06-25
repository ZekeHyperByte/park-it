import asyncio

import pytest

from tests.e2e.simulator.passti_sim import PasstiSimulator


class TestPasstiSimulator:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        sim = PasstiSimulator(host="127.0.0.1", port=0)
        await sim.start()
        assert sim.port > 0
        await sim.stop()

    @pytest.mark.asyncio
    async def test_deduct_response(self):
        sim = PasstiSimulator(host="127.0.0.1", port=0)
        sim.set_next_status("SUCCESS")
        await sim.start()

        reader, writer = await asyncio.open_connection("127.0.0.1", sim.port)
        # Send a simple frame: STX LEN-H LEN-L EF 01 03 DATA LRC
        # Minimal deduct command frame
        frame = bytes.fromhex("02 00 0A EF 01 03 01 02 03 04 05 06 07 08 09".replace(" ", ""))
        writer.write(frame)
        await writer.drain()

        data = await asyncio.wait_for(reader.read(1024), timeout=2.0)
        writer.close()
        await writer.wait_closed()
        await sim.stop()

        assert len(data) > 0
        assert data[0] == 0x02  # STX
