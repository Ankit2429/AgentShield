from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth_token():
    login = client.post("/api/v1/auth/login", data={
        "username": "admin@agentshield.com",
        "password": "admin-password"
    }).json()
    return login["access_token"]

def test_websocket_authentication_success():
    token = get_auth_token()
    with client.websocket_connect(f"/api/v1/ws?token={token}") as websocket:
        # If we reach here, connection was successful
        # We can simulate sending a ping
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"

def test_websocket_authentication_failure():
    from starlette.websockets import WebSocketDisconnect
    
    with client.websocket_connect("/api/v1/ws?token=invalid_token") as websocket:
        try:
            websocket.receive_text()
            assert False, "Should have disconnected"
        except WebSocketDisconnect as e:
            assert e.code == 1008  # Policy Violation
