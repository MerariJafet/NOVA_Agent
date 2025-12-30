import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from nova.api.routes import app

client = TestClient(app)

def test_api_status():
    """Smoke test: API is up and running"""
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"

@patch("nova.core.orquestador.generate_response")
@patch("nova.core.intelligent_router.route")
def test_chat_pipeline_mocked(mock_route, mock_generate):
    """Smoke test: Chat works end-to-end with mocked LLM"""
    
    # Mock Router Decision
    mock_route.return_value = {
        "model": "mixtral", 
        "confidence": 99, 
        "reasoning": "Smoke Test",
        "status": "ok"
    }
    
    # Mock Generation
    mock_generate.return_value = "This is a smoke test response."
    
    # Send Request
    payload = {"message": "Hello smoke test", "session_id": "smoke_1"}
    response = client.post("/api/chat", json=payload)
    
    # Assertions
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    
    # Check Schema
    assert "text" in data
    assert "meta" in data
    
    # Check Content
    assert data["text"] == "This is a smoke test response."
    assert data["meta"]["router"] == "intelligent_router"
    assert data["meta"]["model_selected"] == "mixtral"
    assert data["meta"]["reason"] == "Smoke Test"
    assert "latency_ms" in data["meta"]

def test_chat_clarification():
    """Smoke test: Router clarification response"""
    
    # We can rely on the router logic or mock it to return clarification
    with patch("nova.core.intelligent_router.route") as mock_route:
        mock_route.return_value = {
            "status": "needs_clarification",
            "message": "Please clarify?"
        }
        
        response = client.post("/api/chat", json={"message": "help"})
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["reason"] == "clarification_needed"
        assert data["text"] == "Please clarify?"
