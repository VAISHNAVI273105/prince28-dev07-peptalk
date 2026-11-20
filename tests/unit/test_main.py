from fastapi.testclient import TestClient

from peptalk.main import app


def test_main_home_endpoint():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to PEPTalk!",
        "status": "running",
    }


def test_main_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "peptalk"
    assert data["version"] == "dev"
    assert "env" in data
