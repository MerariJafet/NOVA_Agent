from typing import Dict, Any

from utils.logging import get_logger
from nova.core.intelligent_router import route as intelligent_route
from nova.core import llm_router
from config.settings import settings
from models import ollama_model

logger = get_logger("core.orquestador")


def route_query(message: str, has_image: bool = False) -> dict:
    """Delegate routing to intelligent router; keep compatibility shape."""
    # If LLM brain toggle is active, prefer LLM router (it will fallback to heuristics on timeout)
    result = llm_router.route_with_llm(message, has_image) if settings.USE_LLM_BRAIN else intelligent_route(message, has_image)
    # If router asks for clarification, return that shape directly
    if result.get("status") == "needs_clarification":
        return result
    # Normalize to expected keys
    return {"model": result.get("model"), "confidence": result.get("confidence", 70), "reasoning": result.get("reasoning", "")}


def generate_response(model: str, prompt: str, history: list = []) -> str:
    logger.info("generate_request", model=model)
    try:
        # If Claude is requested but there's no API key configured, fallback immediately to Mixtral
        if "claude" in (model or "") and not settings.claude_api_key:
            logger.warning("claude_no_api_key_fallback", model=model)
            model = "mixtral:8x7b"
        # Prefer a blocking non-streaming call (the client may be synchronous). If you want streaming,
        # change to `stream=True` and consume the generator.
        result = ollama_model.generate(model, prompt, stream=False, timeout=10)
        # result may be a string or raise on network error
        if isinstance(result, str):
            # If the model returned raw JSON with an 'error' field, attempt to clean it
            try:
                parsed = None
                j = None
                try:
                    j = __import__("json").loads(result)
                except Exception:
                    j = None
                if isinstance(j, dict) and "error" in j:
                    # If it's a Claude error and no API key, fallback handled above; otherwise return cleaned message
                    return str(j.get("error"))
            except Exception:
                pass
            return result
        # otherwise, try to coerce generator into a full string
        if hasattr(result, "__iter__"):
            parts = []
            for chunk in result:
                parts.append(chunk)
            return "".join(parts)
    except Exception as e:
        logger.error("generate_request_failed", error=str(e))

    return f"[NOVA fallback reply from {model}]: {prompt[:200]}"
