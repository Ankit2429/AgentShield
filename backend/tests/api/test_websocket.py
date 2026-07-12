from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth_token():
    login = client.post("/api/v1/auth/login", json={
        "email": "admin@agentshield.com",
        "password": "admin-password"
    }).json()
    return login["access_token"]

def test_websocket_authentication_success():
    token = get_auth_token()
    with client.websocket_connect(f"/api/v1/ws?token={token}") as websocket:
        # If we reach here, connection was successful
        # We can simulate sending a ping
        websocket.send_text("ping")
        data = websocket.receive_json()
        assert data["type"] == "pong"

def test_websocket_authentication_failure():
    # FastAPI TestClient raises an exception when WebSocket gets rejected
    import websockets.exceptions
    from starlette.websockets import WebSocketDisconnect
    
    try:
        with client.websocket_connect("/api/v1/ws?token=invalid_token") as websocket:
            assert False, "Should have disconnected"
    except WebSocketDisconnect as e:
        assert e.code == 1008  # Policy Violation
