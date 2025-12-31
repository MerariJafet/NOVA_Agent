import pytest
from nova.core import orquestador


CASES = [
    # Architecture / strategy (expect mixtral:8x7b per Sofía)
    (
        "Analiza trade-offs entre microservicios y monolito para 1M usuarios",
        False,
        "mixtral:8x7b",
    ),
    (
        "Diseña una arquitectura para alta concurrencia y baja latencia",
        False,
        "mixtral:8x7b",
    ),
    (
        "¿Cómo estructurarías la arquitectura para 1 millón de usuarios simultáneos?",
        False,
        "mixtral:8x7b",
    ),
    (
        "Evaluar escalabilidad, tolerancia a fallos y coste de una plataforma distribuida",
        False,
        "mixtral:8x7b",
    ),
    (
        "Comparativa detallada entre CQRS y Event Sourcing en sistemas a escala",
        False,
        "mixtral:8x7b",
    ),
    # Code / debugging (expect dolphin-mistral:7b)
    (
        "Arregla este error de Python: TypeError en función map",
        False,
        "dolphin-mistral:7b",
    ),
    ("Escribe una función en Python para merge sort", False, "dolphin-mistral:7b"),
    ("Debuggea este stacktrace y propone causa probable", False, "dolphin-mistral:7b"),
    (
        "Optimiza este snippet de JavaScript para performance",
        False,
        "dolphin-mistral:7b",
    ),
    ("Genera tests unitarios para esta función en pytest", False, "dolphin-mistral:7b"),
    # Vision (expect moondream:1.8b)
    ("Describe esta foto", True, "moondream:1.8b"),
    ("Analiza la imagen adjunta y enumera objetos detectables", True, "moondream:1.8b"),
    ("¿Qué ves en esta foto?", True, "moondream:1.8b"),
    ("Mira esto y descríbelo", True, "moondream:1.8b"),
    ("Foto: identifica colores dominantes y contexto", True, "moondream:1.8b"),
    # Complex analysis but not architecture (claude or dolphin depending)
    ("Analiza riesgos legales de un modelo de negocio SaaS", False, "mixtral:8x7b"),
    ("Estrategia de producto para lanzar en 3 mercados", False, "mixtral:8x7b"),
    (
        "Análisis financiero completo de unit economics para startup",
        False,
        "mixtral:8x7b",
    ),
    ("Haz un análisis profundo de seguridad para la app móvil", False, "mixtral:8x7b"),
    (
        "Plan detallado de migración de base de datos sin downtime",
        False,
        "mixtral:8x7b",
    ),
    # Short ambiguous requests (needs clarification -> fall back default dolphin)
    ("Ayúdame", False, "dolphin-mistral:7b"),
    ("Explícate", False, "dolphin-mistral:7b"),
    ("¿Qué opinas?", False, "dolphin-mistral:7b"),
    ("¿Qué hago?", False, "dolphin-mistral:7b"),
    ("Info", False, "dolphin-mistral:7b"),
    # Mixed triggers
    (
        "Tengo un error en Python y además necesito escalar la arquitectura",
        False,
        "mixtral:8x7b",
    ),
    ("Imagen + código: analiza el diagrama y genera el código", True, "moondream:1.8b"),
    ("Documenta este proyecto y escribe ejemplos de uso", False, "dolphin-mistral:7b"),
    (
        "Dame una estrategia detallada y ejemplos de código para la integración",
        False,
        "mixtral:8x7b",
    ),
    (
        "Explica conceptos de seguridad y da ejemplos de mitigación",
        False,
        "mixtral:8x7b",
    ),
    # Edge cases
    ("Lista de comandos git útiles", False, "dolphin-mistral:7b"),
    ("Crea un script bash para backup", False, "dolphin-mistral:7b"),
    ("Describe la foto y sugiere tags SEO", True, "moondream:1.8b"),
    ("Analiza la arquitectura y sugiere mejoras de coste", False, "mixtral:8x7b"),
    ("Resumen ejecutivo del proyecto para stakeholders", False, "mixtral:8x7b"),
]


def test_intelligent_router_cases():
    total = len(CASES)
    hits = 0
    for msg, has_image, expected in CASES:
        r = orquestador.route_query(msg, has_image)
        selected = r.get("model")
        # If router asks for clarification return default dolphin as accepted
        if r.get("status") == "needs_clarification":
            selected = "dolphin-mistral:7b"
        if selected == expected:
            hits += 1
        else:
            # allow alternatives in intelligent router output
            alts = r.get("alternatives") or []
            alt_models = [a.get("model") for a in alts]
            if expected in alt_models:
                hits += 1
            else:
                # mark fail
                pytest.fail(
                    f"Message: {msg!r} expected {expected} got {selected} (alts={alt_models})"
                )

    accuracy = hits / total * 100.0
    # ensure at least 87% accuracy
    assert accuracy >= 87.0, f"Accuracy too low: {accuracy}%"
