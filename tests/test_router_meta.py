from fastapi.testclient import TestClient
from unittest.mock import patch
from nova.api.routes import app

client = TestClient(app)


@patch("nova.core.orquestador.generate_response")
@patch("nova.core.intelligent_router.route")
def test_router_meta_propagation(mock_route, mock_generate):
    mock_route.return_value = {
        "model": "mixtral",
        "confidence": 95,
        "reasoning": "Complex analysis",
        "status": "ok",
    }
    mock_generate.return_value = "Response"

    response = client.post(
        "/api/chat", json={"message": "complex query", "session_id": "test_meta"}
    )

    assert response.status_code == 200
    meta = response.json()["meta"]

    assert meta["model_selected"] == "mixtral"
    assert meta["reason"] == "Complex analysis"
