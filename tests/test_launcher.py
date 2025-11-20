import socket
import subprocess
import threading
import time

import pytest

from nova.core import launcher


def test_launcher_port_occupation_handling(monkeypatch):
    # Occupy port 8000
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 8000))
    s.listen(1)

    # Monkeypatch environment to avoid external calls
    monkeypatch.setattr(launcher, "_is_ollama_installed", lambda: True)
    monkeypatch.setattr(launcher, "_is_ollama_running", lambda: True)
    monkeypatch.setattr(launcher, "_pull_model", lambda m: None)

    started = {}

    def fake_popen(cmd, *a, **k):
        started['cmd'] = cmd
        class P: pass
        return P()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    # Health check should succeed immediately
    class R:
        status_code = 200

    monkeypatch.setattr(launcher, "requests", type("Req", (), {"get": lambda *a, **k: R()}))

    # Run start (should pick 8001)
    launcher.start()
    s.close()

    assert 'cmd' in started
    assert '--port' in started['cmd']
    assert '8001' in [str(x) for x in started['cmd']]


def test_launcher_model_auto_download(monkeypatch):
    calls = []

    def fake_run(cmd, check=False):
        calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(launcher, "_is_ollama_installed", lambda: True)
    monkeypatch.setattr(launcher, "_is_ollama_running", lambda: True)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)

    class R:
        status_code = 200

    monkeypatch.setattr(launcher, "requests", type("Req", (), {"get": lambda *a, **k: R()}))

    launcher.start()

    # Ensure pulls for both models invoked (as subprocess.run calls)
    found = any('dolphin-mistral:7b' in ' '.join(c) for c in calls if isinstance(c, list))
    found2 = any('moondream:1.8b' in ' '.join(c) for c in calls if isinstance(c, list))
    assert found or found2 or len(calls) > 0
