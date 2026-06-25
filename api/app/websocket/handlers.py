"""WebSocket endpoint handlers."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.app.middleware.auth import get_current_user
from api.app.websocket.connection_manager import ws_manager
from shared.logging import get_logger
from shared.redis import redis_client

logger = get_logger("ws_handlers")

router = APIRouter()


async def _replay_events(websocket: WebSocket, gate_id: str, since: str) -> None:
    """Stream buffered events for a gate from the Redis Stream since `since`.

    `since` is a Redis Stream id (e.g. "1700000000000-0"). Use "0" or "-" to
    replay everything still buffered. Each event is wrapped with its stream
    id so the client can record the high-water-mark for next reconnect.
    """
    try:
        await redis_client.connect()
        redis = redis_client.client
        # XRANGE is inclusive on the left bound, so add "(" exclusivity by
        # bumping the sequence with "+" suffix not supported here; we emulate
        # by treating empty/0 specially and using exclusive prefix "(" when
        # the caller provides a real id.
        start = "-" if since in ("", "0", "-") else f"({since}"
        entries = await redis.xrange(f"parking.eventlog.{gate_id}", min=start, max="+", count=500)
        for stream_id, fields in entries:
            raw = fields.get("event")
            if raw is None:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            payload["_event_id"] = stream_id
            await websocket.send_text(json.dumps(payload))
        await websocket.send_text(
            json.dumps({"type": "replay_complete", "count": len(entries)})
        )
    except Exception as e:
        logger.warning("ws_replay_failed", gate_id=gate_id, error=str(e))


@router.websocket("/ws/{gate_id}")
async def websocket_endpoint(websocket: WebSocket, gate_id: str) -> None:
    """WebSocket endpoint for real-time gate events.

    Authenticates via httpOnly cookie during upgrade. Clients may send
    `{"type":"replay","since":"<last_event_id>"}` to fill in missed events.
    """
    # Authenticate during handshake
    user = await get_current_user(websocket)
    if user is None:
        await websocket.close(code=1008, reason="Authentication required")
        return

    await ws_manager.connect(gate_id, websocket)
    logger.info("ws_client_connected", gate_id=gate_id, user_id=user.get("sub"))

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            logger.debug("ws_message_received", gate_id=gate_id, data=data)
            handled = False
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict) and parsed.get("type") == "replay":
                    await _replay_events(websocket, gate_id, str(parsed.get("since", "0")))
                    handled = True
            except json.JSONDecodeError:
                pass
            if not handled:
                # Echo back for ping/pong or unrecognized commands.
                # json.dumps escapes the raw client bytes so arbitrary input
                # can't produce a malformed frame.
                await websocket.send_text(json.dumps({"type": "ack", "data": data}))
    except WebSocketDisconnect:
        ws_manager.disconnect(gate_id, websocket)
        logger.info("ws_client_disconnected", gate_id=gate_id)
    except Exception as e:
        ws_manager.disconnect(gate_id, websocket)
        logger.error("ws_error", gate_id=gate_id, error=str(e))
