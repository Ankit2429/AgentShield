from __future__ import annotations

import asyncio
import logging
import time
from fastapi import WebSocket

logger = logging.getLogger("agentshield.ws")


class WebSocketManager:
    """Manages active WebSocket connections for real-time security events."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self.connection_states: dict[WebSocket, float] = {}
        self._janitor_running: bool = False

    async def connect(self, websocket: WebSocket) -> bool:
        """Accept connection and register client.

        Returns:
            bool: True if connection accepted, False if connection pool is full.
        """
        # Connection Limits: maximum 10 concurrent WebSocket clients
        if len(self.active_connections) >= 10:
            await websocket.accept()
            await websocket.close(code=1008, reason="Connection pool full. Max 10 active links allowed.")
            return False

        await websocket.accept()
        self.active_connections.append(websocket)
        now = time.time()
        self.connection_states[websocket] = now

        logger.info(f"WebSocket client registered. Active connections: {len(self.active_connections)}")

        # Start the background socket janitor if not already active
        if not self._janitor_running:
            self._janitor_running = True
            asyncio.create_task(self._prune_dead_sockets_loop())

        return True

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove client registration."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_states:
            del self.connection_states[websocket]
        logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    def update_activity(self, websocket: WebSocket) -> None:
        """Update last seen timestamp for connection idle timeout checking."""
        if websocket in self.connection_states:
            self.connection_states[websocket] = time.time()

    async def broadcast(self, message: dict) -> None:
        """Broadcast JSON message to all active clients."""
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.warning(f"Failed to broadcast to connection, disconnecting client: {exc}")
                self.disconnect(connection)

    async def _prune_dead_sockets_loop(self) -> None:
        """Asynchronous janitor pruning idle or zombie connections."""
        while len(self.active_connections) > 0:
            await asyncio.sleep(10)
            now = time.time()
            for connection in list(self.active_connections):
                last_seen = self.connection_states.get(connection, now)
                # Idle Timeout: prune connections silent for longer than 60 seconds
                if now - last_seen > 60.0:
                    logger.warning("WebSocket client idle timeout exceeded. Pruning connection.")
                    try:
                        await connection.close(code=1008, reason="Idle timeout exceeded.")
                    except Exception:
                        pass
                    self.disconnect(connection)
        self._janitor_running = False


ws_manager = WebSocketManager()
