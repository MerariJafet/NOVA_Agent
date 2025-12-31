from fastapi.testclient import TestClient
from nova.api.routes import app
import nova.core.orquestador as orchestrator


def test_chat_saves_and_returns(monkeypatch):
    # stub generate_response
    monkeypatch.setattr(
        orchestrator,
        "generate_response",
        lambda model, prompt, history=[]: "respuesta de prueba",
    )
    client = TestClient(app)
    r = client.post("/chat", json={"message": "Hola mundo", "session_id": "s-e2e"})
    assert r.status_code == 200
    data = r.json()
    assert "respuesta" in data["response"] or data["response"] == "respuesta de prueba"
