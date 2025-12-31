"""
Sistema de auto-optimización para NOVA.
Ajusta automáticamente las prioridades de los modelos basado en feedback.
"""

from typing import Dict, Any, List
from utils.logging import get_logger

logger = get_logger("core.auto_optimizer")

# Prioridades base de modelos (simuladas)
DEFAULT_PRIORITIES = {
    "dolphin-mistral:7b": 50,
    "mixtral:8x7b": 40,
    "moondream:1.8b": 30,
    "claude-3-haiku": 20,
    "llava:7b": 25,
    "llava:13b": 35,
}

# Estado global de prioridades
_current_priorities = DEFAULT_PRIORITIES.copy()

# Historial de optimizaciones
_optimization_history = []


def auto_optimize(max_change: int = 20, min_feedback: int = 5) -> Dict[str, Any]:
    """
    Ejecuta optimización automática basada en feedback.

    Args:
        max_change: Cambio máximo permitido en prioridad
        min_feedback: Feedback mínimo requerido para optimizar

    Returns:
        Resultado de la optimización
    """
    try:
        from nova.core.feedback_system import analyze_performance

        # Obtener análisis de performance
        perf_data = analyze_performance()

        if perf_data["total_feedback"] < min_feedback:
            return {
                "status": "insufficient_feedback",
                "message": f"Necesario al menos {min_feedback} feedback, actualmente {perf_data['total_feedback']}",
                "changes_applied": [],
            }

        # Calcular nuevos prioridades basados en ratings
        model_performance = perf_data.get("model_performance", {})
        changes_applied = []

        global _current_priorities

        for model, stats in model_performance.items():
            if model in _current_priorities:
                current_priority = _current_priorities[model]
                avg_rating = stats["avg_rating"]

                # Calcular cambio basado en rating (5 estrellas = +max_change, 1 estrella = -max_change)
                rating_change = int((avg_rating - 3.0) * (max_change / 2.0))

                # Aplicar cambio con límites
                new_priority = max(0, min(100, current_priority + rating_change))

                if new_priority != current_priority:
                    changes_applied.append(
                        {
                            "model": model,
                            "old_priority": current_priority,
                            "new_priority": new_priority,
                            "avg_rating": avg_rating,
                            "feedback_count": stats["count"],
                        }
                    )
                    _current_priorities[model] = new_priority

        # Registrar en historial
        _optimization_history.append(
            {
                "timestamp": "now",  # TODO: usar datetime
                "changes_applied": changes_applied,
                "performance_data": perf_data,
            }
        )

        # Mantener solo últimas 10 optimizaciones
        if len(_optimization_history) > 10:
            _optimization_history.pop(0)

        logger.info(
            "auto_optimization_completed",
            changes_applied=len(changes_applied),
            total_feedback=perf_data["total_feedback"],
        )

        return {
            "status": "optimized",
            "changes_applied": changes_applied,
            "total_feedback": perf_data["total_feedback"],
            "average_rating": perf_data["average_rating"],
        }

    except Exception as e:
        logger.error("auto_optimization_failed", error=str(e))
        return {"status": "error", "message": str(e), "changes_applied": []}


def get_current_priorities() -> Dict[str, int]:
    """Obtiene las prioridades actuales de los modelos."""
    return _current_priorities.copy()


def get_optimization_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene el historial de optimizaciones."""
    return _optimization_history[-limit:] if _optimization_history else []
