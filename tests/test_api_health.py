from fastapi.testclient import TestClient
from nova.api.routes import app

client = TestClient(app)


def test_health_check_operational():
    """Verify that the /api/status endpoint is operational."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "version" in data


def test_root_redirect():
    """Verify that the root endpoint redirects to the web UI."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "webui/index.html" in response.headers["location"]
