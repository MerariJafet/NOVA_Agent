"""Simple semantic analyzer for Sprint 2 MVP.

This analyzer is intentionally lightweight: uses keyword heuristics
and basic length/intent checks to produce signals for the intelligent router.
"""
from typing import Dict, Any


def analyze(message: str) -> Dict[str, Any]:
    m = message.lower().strip()
    tokens = m.split()
    signals = {
        "has_question": "?" in message or m.startswith("qué") or m.startswith("como") or m.startswith("cómo"),
        "is_short": len(tokens) <= 2,
        "mentions_architecture": any(k in m for k in ["arquitect", "microserv", "monolit", "escala", "usuarios", "trade-off", "tradeoffs", "trade offs"]),
        "mentions_code": any(k in m for k in ["codigo", "código", "python", "javascript", "script", "programa", "función", "funcion", "debug", "debuggea", "depura", "error", "traceback", "stacktrace", "stack trace", "bug", "git", "bash", "snippet", "snippet"]),
        # Debugging signals: errors, tracebacks, exceptions, TypeError, bug
        "mentions_debug": any(k in m for k in ["error", "exception", "typeerror", "traceback", "stacktrace", "stack trace", "bug", "depura", "debug", "debuggea"]),
        # Explicit code-generation intent (escribe una función, genera código, implementa ...)
        "wants_code_generation": (("escribe" in m or "genera" in m or "implementa" in m or "implementar" in m) and any(k in m for k in ["funci", "function", "merge", "sort", "algoritm", "algoritmo", "ejemplo", "ejemplos"])),
        # Strategy / detailed analysis intent (estrategia detallada, plan, roadmap)
        "mentions_strategy": any(k in m for k in ["estrateg", "estrategia", "detall", "plan", "roadmap", "strategy", "detallada", "detallado"]),
        # Complex / deep-analysis signals: analiza, análisis, explica, riesgos, evaluar, completo, profundo
        "mentions_complex": any(k in m for k in ["analiz", "análisis", "analisis", "analiza", "explica", "concepto", "conceptos", "riesg", "evaluar", "evaluación", "evaluacion", "complet", "profund", "resumen", "ejecutiv"]),
        "mentions_image": any(k in m for k in ["imagen", "foto", "mira", "describe"]),
        # Documentation / examples intent: documentation, ejemplos, tutorial, guía, readme
        "mentions_docs": any(k in m for k in ["document", "documenta", "documentación", "documentacion", "ejemplo", "ejemplos", "ejemplos de uso", "tutorial", "guía", "guia", "readme", "manual", "docs"]),
    }
    return signals
