from typing import Dict, Any
import requests
from config.settings import settings
from nova.core import intelligent_router
from utils.logging import get_logger

logger = get_logger("core.llm_router")


def route_with_llm(message: str, has_image: bool = False) -> Dict[str, Any]:
    """Try using an external LLM-based routing decision. If disabled or request times out (>3s) fall back to heuristic router.

    Expected external API (optional): POST to settings.llm_router_url with JSON {"message":..., "has_image": bool}
    Response expected: {"model": "model_name", "confidence": int, "reasoning": "...", "alternatives": [...]}
    """
    if not settings.USE_LLM_BRAIN:
        return intelligent_router.route(message, has_image)

    try:
        payload = {"message": message, "has_image": has_image}
        # Timeout set to 3s as requested; if LLM router doesn't respond, fallback
        r = requests.post(settings.llm_router_url, json=payload, timeout=3)
        if r.status_code == 200:
            data = r.json()
            # basic validation
            if isinstance(data, dict) and "model" in data:
                logger.info("llm_route_success", model=data.get("model"), confidence=data.get("confidence"))
                return data
    except Exception as e:
        logger.warning("llm_route_failed", error=str(e))

    # fallback to heuristic router
    logger.info("llm_route_fallback", message=message[:120])
    return intelligent_router.route(message, has_image)
