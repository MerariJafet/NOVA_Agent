"""
LLM Router fallback.
Provee una interfaz compatible cuando no hay router LLM externo disponible.
"""
from typing import Dict, Any

from utils.logging import get_logger
from nova.core.intelligent_router import route as heuristic_route

logger = get_logger("core.llm_router")


def route_with_llm(message: str, has_image: bool = False) -> Dict[str, Any]:
    """
    Intenta rutear usando un router LLM externo. Fallback a heurística local.
    """
    try:
        # Placeholder: aquí iría una llamada remota; por ahora devolvemos heurística.
        return heuristic_route(message, has_image)
    except Exception as e:
        logger.error("llm_router_failed_fallback", error=str(e))
        return heuristic_route(message, has_image)
