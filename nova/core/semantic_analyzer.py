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
        "mentions_code": any(k in m for k in ["codigo", "python", "javascript", "script", "programa", "función", "funcion"]),
        "mentions_image": any(k in m for k in ["imagen", "foto", "mira", "describe"]),
    }
    return signals
