from typing import Dict, Any

from utils.logging import get_logger
from nova.core.intelligent_router import route as intelligent_route
from nova.core import llm_router
from config.settings import settings
from models import ollama_model
# from nova.core.cache_system import cache_system  # Commented out to avoid DB issues
import time

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


def generate_response(model: str, prompt: str, history: list | None = None) -> str:
    logger.info("generate_request", model=model)
    history = history or []

    # Limpiar caché expirado periódicamente (cada 100 requests) - commented out
    # if hasattr(generate_response, '_request_count'):
    #     generate_response._request_count += 1
    # else:
    #     generate_response._request_count = 1
    # 
    # if generate_response._request_count % 100 == 0:
    #     expired_count = cache_system.cleanup_expired()
    #     if expired_count > 0:
    #         logger.info("cache_cleanup", expired_entries=expired_count)

    # 1. Verificar caché primero - commented out
    # start_time = time.time()
    # cached_result = cache_system.get_cached_response(prompt, model)
    # 
    # if cached_result:
    #     latency = time.time() - start_time
    #     logger.info("cache_hit", model=model, latency_ms=round(latency * 1000, 2),
    #                hit_count=cached_result["hit_count"])
    #     return cached_result["response"].get("text", str(cached_result["response"]))

    # 2. Cache miss - generar respuesta normal
    try:
        # Sofía policy: always route Claude requests to Mixtral locally (fallback)
        original_model = model
        if model == "claude_code_api":
            logger.info("claude_local_fallback_to_mixtral", original_model=model)
            model = "mixtral:8x7b"

        # Generar respuesta
        start_time = time.time()
        generation_start = time.time()
        result = ollama_model.generate(model, prompt, stream=False, timeout=120)
        generation_time = time.time() - generation_start

        # Normalizar resultado
        if isinstance(result, str):
            response_text = result
        elif hasattr(result, "__iter__"):
            parts = []
            for chunk in result:
                parts.append(chunk)
            response_text = "".join(parts)
        else:
            response_text = str(result)

        # 3. Guardar en caché - commented out
        # metadata = {
        #     "generation_time": generation_time,
        #     "model_used": model,
        #     "original_model": original_model,
        #     "cached_at": time.time()
        # }
        # 
        # cache_key = cache_system.save_to_cache(
        #     query=prompt,
        #     model_name=model,
        #     response={"text": response_text},
        #     metadata=metadata
        # )

        total_latency = time.time() - start_time
        logger.info("response_generated", model=model,
                   generation_ms=round(generation_time * 1000, 2),
                   total_latency_ms=round(total_latency * 1000, 2))

        return response_text

    except Exception as e:
        logger.error("generate_request_failed", error=str(e))
        # No guardar en caché errores
        raise
