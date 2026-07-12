from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_success():
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@agentshield.com",
        "password": "admin-password"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure():
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@agentshield.com",
        "password": "wrong-password"
    })
    assert response.status_code == 401
    assert "detail" in response.json()

def test_me_endpoint():
    login = client.post("/api/v1/auth/login", json={
        "email": "admin@agentshield.com",
        "password": "admin-password"
    }).json()
    token = login["access_token"]
    
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@agentshield.com"
    assert data["role"] == "Admin"

def test_refresh_token():
    login = client.post("/api/v1/auth/login", json={
        "email": "admin@agentshield.com",
        "password": "admin-password"
    }).json()
    refresh_token = login["refresh_token"]
    
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    
    # Try using the old refresh token again (should fail due to revocation)
    response2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response2.status_code == 401
