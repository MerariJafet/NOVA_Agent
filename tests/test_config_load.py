import os
from config.settings import settings


def test_settings_load():
    """Verify that settings can be loaded and have expected default values."""
    assert settings.app_name == "NOVA Core"
    assert settings.version == "1.0.0"
    assert settings.web_port_start == 8003
    assert os.path.isdir("config") or os.path.exists("config/settings.py")


def test_log_path_configuration():
    """Verify log path is configured."""
    assert "logs" in settings.logs_path
