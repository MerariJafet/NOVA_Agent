from typing import Dict, Any

from utils.logging import get_logger
from nova.core.intelligent_router import route as intelligent_route
import requests
from config.settings import settings

logger = get_logger("core.orquestador")


def route_query(message: str, has_image: bool = False) -> dict:
    """Delegate routing to intelligent router; keep compatibility shape."""
    result = intelligent_route(message, has_image)
    # If router asks for clarification, return that shape directly
    if result.get("status") == "needs_clarification":
        return result
    # Normalize to expected keys
    return {"model": result.get("model"), "confidence": result.get("confidence", 70), "reasoning": result.get("reasoning", "")}


def generate_response(model: str, prompt: str, history: list = []) -> str:
    logger.info("generate_request", model=model)
    try:
        payload = {"model": model, "prompt": prompt, "history": history}
        r = requests.post(settings.ollama_generate_url, json=payload, timeout=10)
        if r.status_code == 200:
            try:
                data = r.json()
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

    return f"[NOVA fallback reply from {model}]: {prompt[:200]}"
