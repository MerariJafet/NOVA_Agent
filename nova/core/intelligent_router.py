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
    # If query mixes architecture and code concerns, favor complex-analysis models
    if signals.get("mentions_architecture") and signals.get("mentions_code"):
        if "complex_analysis" in caps or "reasoning" in caps:
            score += 30
    # If query mixes strategy and code (e.g., 'estrategia' + 'ejemplos de código'), favor complex-analysis models
    if signals.get("mentions_strategy") and signals.get("mentions_code"):
        if "complex_analysis" in caps or "reasoning" in caps:
            score += 30
    # If the user requests a deep analysis (legal, financiero, seguridad, producto), prefer complex-analysis models
    if signals.get("mentions_complex") and not signals.get("mentions_code") and not signals.get("mentions_image"):
        if "complex_analysis" in caps or "reasoning" in caps:
            score += 30
    # If message mentions code, handle debugging vs deeper strategy differently
    if signals.get("mentions_code"):
        # If user explicitly wants code generation (e.g., "escribe una función"), strongly prefer code-specialized models
        if signals.get("wants_code_generation"):
            if "code" in caps:
                score += 30
            if "complex_analysis" in caps or "reasoning" in caps:
                score -= 10
        # Quick debugging / error-fix requests should prefer code-specialized models
        elif signals.get("mentions_debug"):
            if "code" in caps:
                score += 25
            if "complex_analysis" in caps or "reasoning" in caps:
                score -= 10
        else:
            # For broader code + strategy requests, prefer code-specialized models stronger
            if "code" in caps:
                score += 30
            elif "complex_analysis" in caps or "reasoning" in caps:
                score += 15
    if signals.get("is_short"):
        score -= 10
    # If the user explicitly asks for documentation/examples (and not code), prefer generalist/assistant models
    if signals.get("mentions_docs") and not signals.get("mentions_code"):
        if "general" in caps or "assistant" in caps:
            score += 20
        # Penalize heavy-reasoning models for pure doc requests
        if "complex_analysis" in caps or "reasoning" in caps:
            score -= 10
    # Prefer generalist models for generic questions without other signals
    if signals.get("has_question") and not (
        signals.get("mentions_architecture") or signals.get("mentions_code") or signals.get("mentions_image")
    ):
        if "general" in caps:
            score += 10
        if "complex_analysis" in caps or "reasoning" in caps:
            score -= 5
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
