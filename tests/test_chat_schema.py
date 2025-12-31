from fastapi.testclient import TestClient
from unittest.mock import patch
from nova.api.routes import app

client = TestClient(app)


@patch("nova.core.orquestador.generate_response")
@patch("nova.core.intelligent_router.route")
def test_chat_schema(mock_route, mock_generate):
    # Mock routing
    mock_route.return_value = {
        "model": "test-model",
        "confidence": 90,
        "reasoning": "Test reasoning",
        "status": "ok",
    }
    # Mock generation
    mock_generate.return_value = "Test response"

    response = client.post(
        "/api/chat", json={"message": "hello", "session_id": "test_schema"}
    )

    assert response.status_code == 200
    data = response.json()

    # Check schema
    assert "text" in data
    assert "meta" in data
    assert data["meta"]["router"] == "intelligent_router"
    assert data["meta"]["model_selected"] == "test-model"
    assert data["meta"]["reason"] == "Test reasoning"
    assert "latency_ms" in data["meta"]
