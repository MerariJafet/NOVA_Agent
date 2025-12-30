"""
Intelligent Router - Sprint 2
Routing basado en scoring con reglas claras y sin conflictos.
"""
from typing import Dict, Any, List
from config.model_profiles import _DATA as model_profiles
from nova.core.semantic_analyzer import analyze
from utils.logging import get_logger

logger = get_logger("core.intelligent_router")


def score_model_for_query(model_name: str, signals: Dict[str, Any]) -> int:
    """
    Calcula score para un modelo basado en señales semánticas.
    
    REGLAS DE PRIORIDAD (de mayor a menor):
    1. Imagen -> moondream (score 1000)
    2. Arquitectura -> mixtral (score base + 200)
    3. Estrategia + Código -> mixtral (score base + 150)
    4. Código simple -> dolphin (score base + 100)
    5. Análisis complejo -> mixtral (score base + 120)
    6. Debug rápido -> dolphin (score base + 80)
    """
    prof = model_profiles.get(model_name, {})
    caps = prof.get("capabilities", [])
    
    # Score base desde perfil
    score = prof.get("priority", 50)
    
    # ==========================================
    # REGLA 1: IMAGEN (prioridad máxima)
    # ==========================================
    if signals.get("mentions_image"):
        if "vision" in caps and model_name == "llava:7b":
            return 1000  # LLaVA 7B es el modelo de visión primario
        elif "vision" in caps and model_name == "moondream:1.8b":
            return 500  # moondream como fallback
        else:
            return 0  # otros modelos descartados
    
    # ==========================================
    # REGLA 2: ARQUITECTURA (mixtral favorecido)
    # ==========================================
    if signals.get("mentions_architecture"):
        if model_name == "mixtral:8x7b":
            score += 200
        elif model_name == "dolphin-mistral:7b":
            score -= 50  # dolphin no es bueno en arquitectura
        return score
    
    # ==========================================
    # REGLA 3: ESTRATEGIA + CÓDIGO (mixtral gana)
    # ==========================================
    if signals.get("mentions_strategy") and signals.get("wants_code_generation"):
        if model_name == "mixtral:8x7b":
            score += 150  # mixtral ideal para estrategia + código
        elif model_name == "dolphin-mistral:7b":
            score -= 30  # dolphin bueno en código pero no estrategia
        return score
    
    # ==========================================
    # REGLA 4: CÓDIGO PURO (dolphin favorecido)
    # ==========================================
    if signals.get("wants_code_generation") or signals.get("mentions_code"):
        if model_name == "dolphin-mistral:7b":
            score += 100  # dolphin excelente para código simple
        elif model_name == "mixtral:8x7b":
            score -= 20  # mixtral es overkill para código simple
        return score
    
    # ==========================================
    # REGLA 5: DEBUG RÁPIDO (dolphin favorecido)
    # ==========================================
    if signals.get("mentions_debug"):
        if model_name == "dolphin-mistral:7b":
            score += 80
        elif model_name == "mixtral:8x7b":
            score -= 10
        return score
    
    # ==========================================
    # REGLA 6: ANÁLISIS COMPLEJO (mixtral favorecido)
    # ==========================================
    if signals.get("mentions_complex") and not signals.get("mentions_code"):
        if model_name == "mixtral:8x7b":
            score += 120
        elif model_name == "dolphin-mistral:7b":
            score -= 30
        return score
    
    # ==========================================
    # REGLA 7: QUERIES CORTAS/SIMPLES (dolphin)
    # ==========================================
    if signals.get("is_short") or signals.get("has_question"):
        if model_name == "dolphin-mistral:7b":
            score += 40
        elif model_name == "moondream:1.8b":
            score -= 50  # moondream no es para texto puro
        elif model_name == "mixtral:8x7b":
            score -= 20
        return score
    
    # Default: retornar score base
    return score


def route(message: str, has_image: bool = False) -> Dict[str, Any]:
    """
    Rutea un mensaje al modelo más apropiado.
    
    Returns:
        {
            "model": "mixtral:8x7b",
            "confidence": 92,
            "reasoning": "Estrategia + código detectados",
            "alternatives": [...]
        }
    """
    # CASO ESPECIAL: Imagen
    if has_image:
        logger.info("routing_image", message=message[:100])
        return {
            "model": "llava:7b",
            "confidence": 100,
            "reasoning": "Imagen adjunta - usando LLaVA 7B end-to-end",
            "alternatives": []
        }
    
    # Análisis semántico
    signals = analyze(message)
    
    logger.info(
        "semantic_signals",
        message=message[:100],
        signals={k: v for k, v in signals.items() if v}  # Solo señales True
    )
    
    # CASO ESPECIAL: Clarificación
    vague_phrases = ["ayudame", "ayuda", "help", "ayúdame"]
    if any(p in message.lower() for p in vague_phrases):
        logger.info("needs_clarification", message=message[:100])
        return {
            "status": "needs_clarification",
            "message": "¿Podrías darme más detalles sobre qué necesitas?"
        }
    
    if signals.get("is_short") and not signals.get("has_question") and len(message.split()) <= 1:
        logger.info("needs_clarification_short", message=message[:100])
        return {
            "status": "needs_clarification",
            "message": "¿Podrías darme más detalles?"
        }
    
    # Scoring de modelos
    scores: List[Dict[str, Any]] = []
    for model_name in model_profiles.keys():
        model_score = score_model_for_query(model_name, signals)
        scores.append({"model": model_name, "score": model_score})
    
    # Ordenar por score
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)
    
    best = scores[0]
    alternatives = [
        {"model": s["model"], "score": s["score"]} 
        for s in scores[1:3]
    ]
    
    # Calcular confianza (0-100)
    confidence = min(100, max(50, 50 + (best["score"] - 50)))
    
    # Reasoning legible
    active_signals = [k for k, v in signals.items() if v]
    reasoning = f"Señales detectadas: {', '.join(active_signals)}"
    
    logger.info(
        "routing_decision",
        model=best["model"],
        score=best["score"],
        confidence=confidence,
        alternatives=alternatives
    )
    
    return {
        "model": best["model"],
        "confidence": confidence,
        "reasoning": reasoning,
        "alternatives": alternatives
    }
