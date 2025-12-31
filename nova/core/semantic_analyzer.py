"""Simple semantic analyzer for Sprint 2 MVP.

This analyzer is intentionally lightweight: uses keyword heuristics
and basic length/intent checks to produce signals for the intelligent router.
"""

from typing import Dict, Any


def analyze(message: str) -> Dict[str, Any]:
    """
    Analiza un mensaje y extrae señales semánticas.

    Returns:
        Dict con señales booleanas (has_question, mentions_code, etc.)
    """
    m = message.lower().strip()
    tokens = m.split()

    # Keywords para detección
    architecture_keywords = [
        "arquitect",
        "microserv",
        "monolit",
        "escala",
        "usuarios",
        "trade-off",
        "tradeoffs",
        "trade offs",
        "diseño",
        "diseña",
    ]

    code_keywords = [
        "codigo",
        "código",
        "python",
        "javascript",
        "script",
        "programa",
        "función",
        "funcion",
        "debug",
        "debuggea",
        "depura",
        "error",
        "traceback",
        "stacktrace",
        "stack trace",
        "bug",
        "git",
        "bash",
        "snippet",
        "implementa",
        "implementar",
    ]

    debug_keywords = [
        "error",
        "exception",
        "typeerror",
        "traceback",
        "stacktrace",
        "stack trace",
        "bug",
        "depura",
        "debug",
        "debuggea",
        "arregla",
        "fix",
    ]

    # ✅ ARREGLO CRÍTICO: Detectar "ejemplo" Y "ejemplos"
    code_generation_keywords = [
        "funci",
        "function",
        "merge",
        "sort",
        "algoritm",
        "algoritmo",
        "ejemplo",
        "ejemplos",  # ← AMBAS FORMAS
    ]

    code_generation_verbs = [
        "escribe",
        "genera",
        "implementa",
        "implementar",
        "dame",
        "crea",
        "desarrolla",
        "programa",
        "optimiza",
        "optimizar",
        "mejora",
        "mejorar",
    ]

    strategy_keywords = [
        "estrateg",
        "estrategia",
        "detall",
        "plan",
        "roadmap",
        "strategy",
        "detallada",
        "detallado",
    ]

    complex_keywords = [
        "analiz",
        "análisis",
        "analisis",
        "analiza",
        "explica",
        "concepto",
        "conceptos",
        "riesg",
        "evaluar",
        "evaluación",
        "evaluacion",
        "complet",
        "profund",
        "resumen",
        "ejecutiv",
        "estrateg",
        "plan",
        "detall",
    ]

    image_keywords = ["imagen", "foto", "mira", "describe"]

    docs_keywords = [
        "document",
        "documenta",
        "documentación",
        "documentacion",
        "tutorial",
        "guía",
        "guia",
        "readme",
        "manual",
        "docs",
    ]

    # Detectar señales básicas primero
    mentions_code = any(k in m for k in code_keywords)
    mentions_debug = any(k in m for k in debug_keywords)

    # Detectar señales
    signals = {
        "has_question": (
            "?" in message
            or m.startswith(("qué", "que", "como", "cómo", "cuál", "cual"))
        ),
        "is_short": len(tokens) <= 2,
        "mentions_architecture": any(k in m for k in architecture_keywords),
        "mentions_code": mentions_code,
        "mentions_debug": mentions_debug,
        # ✅ ARREGLO CRÍTICO: Lógica corregida
        "wants_code_generation": (
            any(v in m for v in code_generation_verbs)
            and (any(k in m for k in code_generation_keywords) or mentions_code)
        ),
        "mentions_strategy": any(k in m for k in strategy_keywords),
        "mentions_complex": any(k in m for k in complex_keywords),
        "mentions_image": any(k in m for k in image_keywords),
        "mentions_docs": any(k in m for k in docs_keywords),
    }

    return signals
