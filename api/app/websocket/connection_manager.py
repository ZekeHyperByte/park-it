"""WebSocket connection manager."""

from collections import defaultdict

from fastapi import WebSocket

from shared.logging import get_logger

logger = get_logger("ws_manager")


class ConnectionManager:
    """Manage WebSocket connections per gate."""

    def __init__(self) -> None:
        # gate_id -> set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, gate_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self._connections[gate_id].add(websocket)
        logger.info("ws_connected", gate_id=gate_id, total=len(self._connections[gate_id]))

    def disconnect(self, gate_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self._connections[gate_id].discard(websocket)
        logger.info("ws_disconnected", gate_id=gate_id, total=len(self._connections[gate_id]))
        if not self._connections[gate_id]:
            del self._connections[gate_id]

    async def send_to_gate(self, gate_id: str, message: str) -> None:
        """Send a message to all connections for a specific gate."""
        disconnected = []
        for ws in list(self._connections.get(gate_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(gate_id, ws)

    async def broadcast(self, message: str) -> None:
        """Send a message to all connected clients."""
        for gate_id in list(self._connections.keys()):
            await self.send_to_gate(gate_id, message)

    def get_connection_count(self, gate_id: str | None = None) -> int:
        """Get number of active connections."""
        if gate_id:
            return len(self._connections.get(gate_id, set()))
        return sum(len(conns) for conns in self._connections.values())


# Global instance (per-process)
ws_manager = ConnectionManager()
