import pytest
import sys
from unittest.mock import MagicMock, patch

def test_imports():
    """Verify core modules can be imported without syntax errors."""
    try:
        import nova.core.launcher
        import nova.core.orquestador
        import nova.core.intelligent_router
        import nova.core.memoria
        import nova.core.episodic_memory
        import nova.core.semantic_memory
        import nova.api.routes
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_launcher_start_structure():
    """Verify launcher.start() returns the correct dictionary structure (mocked)."""
    with patch("subprocess.Popen") as mock_popen:
        with patch("nova.core.launcher._is_ollama_installed", return_value=True):
            with patch("nova.core.launcher._is_ollama_running", return_value=True):
                with patch("nova.core.launcher._pull_model"):
                    with patch("requests.get") as mock_get:
                        mock_get.return_value.status_code = 200
                        from nova.core.launcher import start
                        
                        # Mock find_free_port
                        with patch("nova.core.launcher._find_free_port", return_value=8000):
                            res = start(port=8000)
                            
                            assert isinstance(res, dict)
                            assert "port" in res
                            assert "uvicorn_pid" in res
                            assert "ollama_pid" in res
                            assert "ollama_managed" in res
                            assert res["port"] == 8000

def test_orquestador_routing_logic():
    """Verify basic keyword routing logic in orquestador."""
    from nova.core.orquestador import route_query
    
    # Test image routing
    res = route_query("what is in this image?", has_image=True)
    assert res["model"] == "moondream:1.8b"
    
    # Test default routing (assuming 'hola' isn't a high-priority trigger for a specific model)
    res = route_query("hola")
    assert "model" in res
    assert isinstance(res["confidence"], int)
