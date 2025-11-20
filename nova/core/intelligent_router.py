from typing import Dict, Any, List
import json
from config.model_profiles import _DATA as model_profiles  # load dict directly
from nova.core.semantic_analyzer import analyze
from utils.logging import get_logger

logger = get_logger("core.intelligent_router")


def score_model_for_query(model_name: str, signals: Dict[str, Any]) -> int:
    # Simple scoring: boost if capabilities match signals
    prof = model_profiles.get(model_name, {})
    caps = prof.get("capabilities", [])
    score = prof.get("priority", 0)
    if signals.get("mentions_image") and "vision" in caps:
        score += 30
    if signals.get("mentions_architecture") and ("complex_analysis" in caps or "reasoning" in caps):
        score += 25
    if signals.get("mentions_code") and "code" in caps:
        score += 20
    if signals.get("is_short"):
        score -= 10
    return score


def route(message: str, has_image: bool = False) -> Dict[str, Any]:
    """Return routing decision with model, confidence, reasoning and alternatives."""
    if has_image:
        logger.info("routing_image", message=message)
        return {"model": "moondream:1.8b", "confidence": 100, "reasoning": "Imagen adjunta" , "alternatives": []}

    signals = analyze(message)

    # Quick clarification path: very short or vague requests
    vague_phrases = ["ayudame", "ayuda", "help", "help me", "ayúdame"]
    if has_image:
        logger.info("routing_image", message=message)
        return {"model": "moondream:1.8b", "confidence": 100, "reasoning": "Imagen adjunta" , "alternatives": []}

    # Clarification if explicit vague phrase present, or very single-token short without question
    if any(p in message.lower() for p in vague_phrases):
        logger.info("needs_clarification", message=message)
        return {"status": "needs_clarification", "message": "¿Podrías darme más detalles sobre qué necesitas?"}
    if signals.get("is_short") and not signals.get("has_question") and len(message.split()) <= 1:
        logger.info("needs_clarification_short", message=message)
        return {"status": "needs_clarification", "message": "¿Podrías darme más detalles sobre qué necesitas?"}

    # Score available models
    scores: List[Dict[str, Any]] = []
    for m in model_profiles.keys():
        s = score_model_for_query(m, signals)
        scores.append({"model": m, "score": s})

    scores = sorted(scores, key=lambda x: x["score"], reverse=True)
    best = scores[0]
    second = scores[1] if len(scores) > 1 else None

    # Map raw score to a confidence: bias towards higher confidence for higher scores
    confidence = min(100, 50 + best["score"])  # base 50 + score -> ensures >75 for significant scores
    alternatives = []
    if second:
        alternatives.append({"model": second["model"], "score": second["score"]})

    reasoning = "Query clasificó por señales: " + ",".join([k for k,v in signals.items() if v])

    logger.info("routing_result", chosen=best["model"], score=best["score"], alternatives=alternatives)

    return {"model": best["model"], "confidence": confidence, "reasoning": reasoning, "alternatives": alternatives}
