"""E2E tests for booth bridge WebSocket e-money deduct flow."""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
import websockets

from booth_bridge.serial_manager import SerialManager
from booth_bridge.websocket_server import WebSocketServer
from protocols.passti.frame import _lrc


def _build_deduct_success_frame() -> bytes:
    """Build a PASSTI deduct SUCCESS response frame parseable by parse_response."""
    # Body layout per parse_deduct_response (40 bytes):
    # [0] card_type_code, [1:9] mid (8), [9:13] tid (4), [13:20] datetime (7),
    # [20:28] card_number (8), [28:32] deducted (4), [32:36] remaining (4),
    # [36:40] trans_counter (4)
    body = (
        bytes([0x02])  # Mandiri eMoney
        + b"12345678"  # mid (8 bytes)
        + b"8765"  # tid (4 bytes)
        + bytes.fromhex("26042612000000")[:7]  # datetime (7 bytes)
        + bytes.fromhex("1234567890123456")  # card_number (8 bytes)
        + (500).to_bytes(4, "big")  # deducted = 500
        + (8700).to_bytes(4, "big")  # remaining = 8700
        + (1).to_bytes(4, "big")  # trans_counter = 1
    )
    # parse_response expects: resp_code=0x00, status=(0x00,0x00,0x00), then body
    payload = bytes([0x00, 0x00, 0x00, 0x00]) + body
    lh = (len(payload) >> 8) & 0xFF
    ll = len(payload) & 0xFF
    lrc_val = _lrc(bytes([lh, ll]) + payload)
    return bytes([0x02, lh, ll]) + payload + bytes([lrc_val])


@pytest.mark.asyncio
async def test_booth_bridge_emoney_deduct_success():
    """Mocked PASSTI SUCCESS deduct results in correct JSON response and API call."""
    serial_manager = MagicMock(spec=SerialManager)
    serial_manager.send.return_value = _build_deduct_success_frame()

    api_config = {
        "base_url": "http://localhost:8000",
        "api_key": "test-api-key",
    }

    ws_server = WebSocketServer(serial_manager, port=0, api_config=api_config)
    await ws_server.start()
    port = ws_server._server.sockets[0].getsockname()[1]

    captured_api_calls = []

    async def mock_call_api(payload: dict) -> None:
        captured_api_calls.append(payload)

    try:
        with patch.object(ws_server, "_call_api_booth_result", side_effect=mock_call_api):
            async with websockets.connect(f"ws://localhost:{port}") as ws:
                message = {
                    "action": "emoney_deduct",
                    "amount": 500,
                    "gate_id": "GOUT01",
                    "gate_out_id": 1,
                }
                await ws.send(json.dumps(message))
                response_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                # Allow background API call task to execute
                await asyncio.sleep(0.2)

        response = json.loads(response_raw)

        # 1. Correct structured JSON response to frontend
        assert response["action"] == "emoney_deduct_result"
        assert response["status"] == "SUCCESS"
        assert response["card_number"] == "1234567890123456"
        assert response["deduct_amount"] == 500
        assert response["balance_before"] == 9200  # 8700 + 500
        assert response["balance_after"] == 8700
        assert response["transaction_counter"] == 1
        assert response["raw_response_hex"] is not None
        assert response["gate_id"] == "GOUT01"
        assert response["gate_out_id"] == 1

        # 2. API booth-result endpoint called with correct data
        assert len(captured_api_calls) == 1
        api_payload = captured_api_calls[0]
        assert api_payload["gate_id"] == "GOUT01"
        assert api_payload["gate_out_id"] == 1
        assert api_payload["card_number"] == "1234567890123456"
        assert api_payload["status"] == "SUCCESS"
        assert api_payload["deduct_amount"] == 500
        assert api_payload["balance_before"] == 9200
        assert api_payload["balance_after"] == 8700
        assert api_payload["transaction_counter"] == 1
        assert api_payload["raw_response_hex"] is not None

        # Verify serial_manager was called for emoney_reader
        serial_manager.send.assert_called_once()
        call_args = serial_manager.send.call_args[0]
        assert call_args[0] == "emoney_reader"

    finally:
        await ws_server.stop()
