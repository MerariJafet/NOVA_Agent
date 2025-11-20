from fastapi.testclient import TestClient
from nova.api.routes import app


def test_status_endpoint():
    client = TestClient(app)
    r = client.get("/status")
    assert r.status_code == 200
    d = r.json()
    assert d.get("status") == "operational"
