from fastapi.testclient import TestClient
from nova.api.routes import app

client = TestClient(app)


def test_status():
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"
