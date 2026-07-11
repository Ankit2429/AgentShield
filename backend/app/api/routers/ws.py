import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from app.core.ws import ws_manager
from app.config import settings
from app.utils.jwt import verify_token

logger = logging.getLogger("agentshield.ws_router")
router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accept and manage a authenticated real-time telemetry link."""
    # 1. Authenticate WebSocket Connection
    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication failed. JWT token query parameter is missing."
        )
        return

    try:
        verify_token(token=token, secret_key=settings.SECRET_KEY, expected_type="access")
    except ValueError as exc:
        await websocket.accept()
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Authentication token verification failed: {exc}"
        )
        return

    # 2. Register Connection
    connected = await ws_manager.connect(websocket)
    if not connected:
        return

    # 3. Read Loop with limits
    try:
        while True:
            # Enforce Message Size Limits: maximum 64KB message
            data = await websocket.receive_text()
            if len(data) > 65536:
                logger.warning("Oversized WebSocket message received. Closing connection.")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Message payload size exceeds 64KB.")
                ws_manager.disconnect(websocket)
                break

            # Update activity state
            ws_manager.update_activity(websocket)

            # Enforce expected messages: only ping heartbeats are whitelisted
            if data == "ping":
                await websocket.send_text("pong")
            else:
                logger.warning(f"Unexpected non-ping client message received: {data[:100]}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unexpected message command.")
                ws_manager.disconnect(websocket)
                break
    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket.")
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.error(f"WebSocket execution error: {exc}")
        ws_manager.disconnect(websocket)
