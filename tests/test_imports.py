import pytest


def test_core_imports():
    """Verify that all core modules can be imported without external service dependencies."""
    try:
        from nova.core import launcher
        from nova.core import orquestador
        from nova.core import memoria
        from nova.core import intelligent_router
        from nova.api import routes

        assert launcher is not None
        assert orquestador is not None
        assert memoria is not None
        assert intelligent_router is not None
        assert routes is not None
    except ImportError as e:
        pytest.fail(f"Core import failed: {e}")


def test_api_models_import():
    """Verify API models import."""
    from nova.api import models

    assert models.ChatRequest is not None
    assert models.ChatResponse is not None
