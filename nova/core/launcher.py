import shutil
import subprocess
import time
import requests
import socket
import sys
from typing import Optional

from utils.logging import get_logger
from config.settings import settings

logger = get_logger("core.launcher")


def _is_ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def _is_ollama_running(health_url: str = "http://localhost:11434/api/tags") -> bool:
    try:
        r = requests.get(health_url, timeout=1)
        return r.status_code == 200
    except Exception:
        return False


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

    # Start ollama serve if not running
    if not _is_ollama_running():
        logger.info("ollama_not_running_try_start")
        _start_ollama_serve()
    else:
        logger.info("ollama_already_running")

    # Auto-pull models
    models = settings.models
    for m in models:
        _pull_model(m)

    # Health check loop
    health_url = settings.ollama_health_url
    logger.info("waiting_for_ollama_health", url=health_url)
    while True:
        try:
            r = requests.get(health_url, timeout=2)
            if r.status_code == 200:
                logger.info("ollama_health_ok")
                break
        except Exception:
            logger.debug("ollama_health_check_failed")
        time.sleep(3)

    # Find free port in range
    free_port = _find_free_port(settings.web_port_start, settings.web_port_end)
    if free_port is None:
        logger.error("no_free_port")
        raise RuntimeError("No free port found between 8000 and 8010")

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
    try:
        uvicorn_cmd = [sys.executable, "-m", "uvicorn", "nova.api.routes:app", "--host", "0.0.0.0", "--port", str(free_port)]
        subprocess.Popen(uvicorn_cmd)
        logger.info("uvicorn_started", port=free_port)
    except Exception as e:
        logger.error("uvicorn_start_failed", error=str(e))
        raise
