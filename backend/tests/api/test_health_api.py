from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    # Fix the old "/health" path to "/api/v1/health"
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "engines" in data
    assert data["engines"]["DetectionEngine"] == "ready"
