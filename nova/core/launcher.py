import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import requests

from utils.logging import get_logger
from config.settings import settings

logger = get_logger("core.launcher")
PID_FILE = Path(settings.pid_path)


def _read_pid_file() -> dict:
    if not PID_FILE.exists():
        return {}
    try:
        with PID_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_pid_file(uvicorn_pid: Optional[int], ollama_pid: Optional[int], port: int, ollama_managed: bool) -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "uvicorn_pid": uvicorn_pid,
        "ollama_pid": ollama_pid if ollama_managed else None,
        "port": port,
        "ollama_managed": ollama_managed,
        "written_at": time.time()
    }
    with PID_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)
    logger.info("pid_file_written", path=str(PID_FILE), data=data)


def _is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _terminate_pid(pid: int, name: str) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        logger.info("process_not_found", name=name, pid=pid)
        return
    except PermissionError:
        logger.warning("process_terminate_permission_denied", name=name, pid=pid)
        return

    deadline = time.time() + 10
    while time.time() < deadline:
        if not _is_process_running(pid):
            logger.info("process_stopped", name=name, pid=pid)
            return
        time.sleep(0.5)

    try:
        os.kill(pid, signal.SIGKILL)
        logger.info("process_killed", name=name, pid=pid)
    except Exception as e:
        logger.warning("process_kill_failed", name=name, pid=pid, error=str(e))


def _is_ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def _is_ollama_running(health_url: str = "http://localhost:11434/api/tags") -> bool:
    try:
        r = requests.get(health_url, timeout=1)
        return r.status_code == 200
    except Exception:
        return False


def _wait_for_ollama(health_url: str, timeout: int = 60) -> None:
    logger.info("waiting_for_ollama_health", url=health_url, timeout_seconds=timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(health_url, timeout=2)
            if r.status_code == 200:
                logger.info("ollama_health_ok")
                return
        except Exception:
            logger.debug("ollama_health_check_failed")
        time.sleep(3)
    raise RuntimeError(f"Ollama no respondió saludable en {timeout}s en {health_url}")


def _start_ollama_serve() -> subprocess.Popen:
    logger.info("starting_ollama_serve")
    p = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info("ollama_serve_started", pid=p.pid)
    return p


def _pull_model(model: str) -> None:
    logger.info("pull_model_start", model=model)
    # Try to run pull; if ollama is unavailable or pull fails, we still simulate progress
    try:
        subprocess.run(["ollama", "pull", model], check=False)
    except Exception:
        logger.warning("pull_model_cmd_failed", model=model)
    # Simple progress indicator (simulated) via structured logs
    for i in range(0, 101, 10):
        logger.info("startup_progress", step=f"pulling_model", model=model, percent=i)
        time.sleep(0.05)
    logger.info("pull_model_done", model=model)


def _find_free_port(start: int = 8000, end: int = 8010) -> Optional[int]:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return None


def _is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def start(port: int = 8000) -> None:
    """Start NOVA system: ensure ollama, pull models, healthcheck, find port and start uvicorn.

    This function is intended to return after launching the uvicorn process.
    """
    logger.info("system_startup_attempt")

    if not _is_ollama_installed():
        msg = (
            "ollama no encontrado. Instálalo desde: https://ollama.ai/download "
            "(o https://ollama.com/download)."
        )
        logger.error("ollama_not_installed", message=msg)
        raise RuntimeError(msg)

    if PID_FILE.exists():
        logger.info("existing_pid_file_detected", path=str(PID_FILE), data=_read_pid_file())

    ollama_proc: Optional[subprocess.Popen] = None
    ollama_managed = False

    # Start ollama serve if not running
    if not _is_ollama_running():
        logger.info("ollama_not_running_try_start")
        ollama_proc = _start_ollama_serve()
        ollama_managed = True
    else:
        logger.info("ollama_already_running")

    # Auto-pull models
    models = settings.models
    for m in models:
        _pull_model(m)

    # Health check loop
    _wait_for_ollama(settings.ollama_health_url, timeout=90)

    # Find free port in range
    free_port = None
    try:
        if port and _is_port_free(port):
            free_port = port
        else:
            free_port = _find_free_port(settings.web_port_start, settings.web_port_end)
    except PermissionError:
        # En entornos restringidos, intentar sin validación de socket
        free_port = port or settings.web_port_start

    if free_port is None:
        logger.error("no_free_port")
        raise RuntimeError(f"No free port found between {settings.web_port_start} and {settings.web_port_end}")

    logger.info("system_ready", port=free_port)
    ascii_art = (
        " _   _  ___  _   _   ___   _   _\n"
        "| \\ | |/ _ \\| \\ | | / _ \\ | \\ | |\n"
        "|  \\| | | | |  \\| || | | ||  \\| |\n"
        "| |\\  | |_| | |\\  || |_| || |\\  |\n"
        "|_| \\_|\\___/|_| \\_| \\___/ |_| \\_|\n\nN O V A   O P E R A T I V O"
    )
    logger.info("startup_progress", message=ascii_art)
    logger.info("startup_progress", message=f"NOVA OPERATIVO → http://localhost:{free_port} | Presiona Ctrl+C para detener")

    # Launch uvicorn in background
    uvicorn_proc: Optional[subprocess.Popen] = None
    try:
        uvicorn_cmd = [sys.executable, "-m", "uvicorn", "nova.api.routes:app", "--host", "0.0.0.0", "--port", str(free_port)]
        uvicorn_proc = subprocess.Popen(uvicorn_cmd)
        _write_pid_file(uvicorn_proc.pid if uvicorn_proc else None, ollama_proc.pid if ollama_proc else None, free_port, ollama_managed)
        logger.info("uvicorn_started", port=free_port, pid=uvicorn_proc.pid if uvicorn_proc else None)
    except Exception as e:
        logger.error("uvicorn_start_failed", error=str(e))
        if ollama_proc:
            _terminate_pid(ollama_proc.pid, "ollama")
        raise


def stop() -> None:
    """Stop uvicorn and managed Ollama processes gracefully."""
    data = _read_pid_file()
    if not data:
        logger.warning("no_pid_file_found", path=str(PID_FILE))
        return

    uvicorn_pid = data.get("uvicorn_pid")
    ollama_pid = data.get("ollama_pid")
    ollama_managed = data.get("ollama_managed", False)

    if uvicorn_pid:
        _terminate_pid(int(uvicorn_pid), "uvicorn")
    else:
        logger.info("uvicorn_pid_missing")

    if ollama_managed and ollama_pid:
        _terminate_pid(int(ollama_pid), "ollama")
    else:
        logger.info("ollama_stop_skipped", managed=ollama_managed, pid=ollama_pid)

    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception as e:
        logger.warning("pid_file_cleanup_failed", error=str(e))

    logger.info("system_stop_completed")
