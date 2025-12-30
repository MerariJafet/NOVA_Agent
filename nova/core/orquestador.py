from typing import Dict, List

import json
import requests
from utils.logging import get_logger

logger = get_logger("core.orquestador")

with open("config/routing_rules.json", "r", encoding="utf-8") as f:
    ROUTING_RULES = json.load(f)


def _tokenize(text: str) -> List[str]:
    return [t.strip() for t in text.lower().replace("?", " ").replace("¿", " ").split() if t.strip()]


def route_query(message: str, has_image: bool = False) -> dict:
    """Route a model based on keywords and image presence.

    Returns dict: {model: str, confidence: int, reasoning: str}
    """
    if has_image:
        logger.info("routing_image_detected")
        return {"model": "moondream:1.8b", "confidence": 100, "reasoning": "Imagen adjunta"}

    msg = message.lower()
    tokens = _tokenize(message)

    # Exact token match -> 100
    for rule, cfg in ROUTING_RULES.items():
        triggers = cfg.get("triggers", [])
        for t in triggers:
            if t in tokens:
                logger.info("routing_exact_match", rule=rule, trigger=t)
                return {"model": cfg["model"], "confidence": 100, "reasoning": f"Trigger exacto: {t}"}

    # Substring match -> 90
    for rule, cfg in ROUTING_RULES.items():
        triggers = cfg.get("triggers", [])
        for t in triggers:
            if t in msg:
                logger.info("routing_partial_match", rule=rule, trigger=t)
                return {"model": cfg["model"], "confidence": 90, "reasoning": f"Trigger parcial: {t}"}

    # Default
    default_model = ROUTING_RULES["default"]["model"]
    logger.info("routing_default", model=default_model)
    return {"model": default_model, "confidence": 70, "reasoning": "Default routing"}


from config.settings import settings


def generate_response(model: str, prompt: str, history: list = []) -> str:
    logger.info("generate_request", model=model)
    try:
        payload = {"model": model, "prompt": prompt, "stream": False}
        r = requests.post(settings.ollama_generate_url, json=payload, timeout=60)
        if r.status_code == 200:
            try:
                data = r.json()
                # adapt to different response shapes
                if isinstance(data, dict) and "result" in data:
                    return data["result"]
                if isinstance(data, dict) and "text" in data:
                    return data["text"]
                return r.text
            except Exception:
                return r.text
        else:
            logger.warning("generate_non_200", status=r.status_code)
    except Exception as e:
        logger.error("generate_request_failed", error=str(e))

    # Fallback simple echo with diagnosis to avoid silent failures
    return (
        f"[NOVA fallback: el motor '{model}' no respondió. "
        f"Se usó eco temporal. Prompt parcial]: {prompt[:200]}"
    )


def ping_engines() -> dict:
    """Simple health check for Ollama/engines to quickly surface connectivity issues."""
    status = {"ollama": "unknown"}
    try:
        r = requests.get(settings.ollama_health_url, timeout=10)
        if r.status_code == 200:
            status["ollama"] = "ok"
        else:
            status["ollama"] = f"http_{r.status_code}"
    except Exception as e:
        status["ollama"] = f"error:{e.__class__.__name__}"
        logger.error("ollama_health_failed", error=str(e))
    return status
