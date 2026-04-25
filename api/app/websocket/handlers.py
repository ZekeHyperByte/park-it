"""WebSocket endpoint handlers."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.app.middleware.auth import get_current_user
from api.app.websocket.connection_manager import ws_manager
from shared.logging import get_logger

logger = get_logger("ws_handlers")

router = APIRouter()


@router.websocket("/ws/{gate_id}")
async def websocket_endpoint(websocket: WebSocket, gate_id: str) -> None:
    """WebSocket endpoint for real-time gate events.

    Authenticates via httpOnly cookie during upgrade.
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
            # Echo back for ping/pong or handle commands
            await websocket.send_text(f'{{"type":"ack","data":{data}}}')
    except WebSocketDisconnect:
        ws_manager.disconnect(gate_id, websocket)
        logger.info("ws_client_disconnected", gate_id=gate_id)
    except Exception as e:
        ws_manager.disconnect(gate_id, websocket)
        logger.error("ws_error", gate_id=gate_id, error=str(e))
