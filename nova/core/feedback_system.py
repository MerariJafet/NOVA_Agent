"""
Feedback System - Sprint 3
Sistema de retroalimentación humana para que NOVA aprenda y mejore automáticamente.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import sqlite3
from nova.core.memoria import _get_conn
from utils.logging import get_logger

logger = get_logger("core.feedback_system")


def record_feedback(
    message_id: int, session_id: str, rating: int, comment: str = ""
) -> int:
    """
    Registra feedback humano sobre una respuesta.

    Args:
        message_id: ID de la respuesta en la tabla messages
        session_id: ID de sesión del usuario
        rating: 1-5 (1=malo, 5=excelente)
        comment: Comentario opcional

    Returns:
        feedback_id: ID del feedback registrado
    """
    with _get_conn() as conn:
        c = conn.cursor()

        # Verificar que el message_id existe
        c.execute("SELECT id, model_used FROM messages WHERE id = ?", (message_id,))
        message = c.fetchone()
        if not message:
            raise ValueError(f"Message ID {message_id} no encontrado")

        model_used = message[1]

        # Insertar feedback
        c.execute(
            """
            INSERT INTO feedback (message_id, session_id, rating, comment, model_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (message_id, session_id, rating, comment, model_used, datetime.now()),
        )

        feedback_id = c.lastrowid
        conn.commit()

        logger.info(
            "feedback_recorded",
            feedback_id=feedback_id,
            rating=rating,
            model=model_used,
        )
        return feedback_id


def analyze_performance(days: int = 7) -> Dict[str, Any]:
    """
    Analiza el rendimiento de los modelos basado en feedback humano.

    Args:
        days: Número de días hacia atrás para analizar

    Returns:
        Dict con métricas por modelo y sugerencias de mejora
    """
    cutoff_date = datetime.now() - timedelta(days=days)

    with _get_conn() as conn:
        c = conn.cursor()

        # Obtener estadísticas por modelo
        c.execute(
            """
            SELECT
                model_used,
                COUNT(*) as total_feedback,
                AVG(rating) as avg_rating,
                MIN(rating) as min_rating,
                MAX(rating) as max_rating,
                SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as good_ratings,
                SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as bad_ratings
            FROM feedback
            WHERE created_at >= ?
            GROUP BY model_used
            ORDER BY avg_rating DESC
        """,
            (cutoff_date,),
        )

        model_stats = {}
        for row in c.fetchall():
            model, total, avg, min_r, max_r, good, bad = row
            model_stats[model] = {
                "total_feedback": total,
                "avg_rating": round(avg, 2) if avg else 0,
                "min_rating": min_r,
                "max_rating": max_r,
                "good_ratings": good,
                "bad_ratings": bad,
                "good_percentage": round((good / total) * 100, 1) if total > 0 else 0,
                "bad_percentage": round((bad / total) * 100, 1) if total > 0 else 0,
            }

        # Análisis de tendencias temporales
        c.execute(
            """
            SELECT
                DATE(created_at) as date,
                model_used,
                AVG(rating) as daily_avg,
                COUNT(*) as daily_count
            FROM feedback
            WHERE created_at >= ?
            GROUP BY DATE(created_at), model_used
            ORDER BY date DESC, daily_avg DESC
        """,
            (cutoff_date,),
        )

        trends = {}
        for row in c.fetchall():
            date, model, daily_avg, daily_count = row
            if model not in trends:
                trends[model] = []
            trends[model].append(
                {"date": date, "avg_rating": round(daily_avg, 2), "count": daily_count}
            )

        # Análisis de tipos de error por modelo
        error_analysis = _analyze_error_patterns(conn, cutoff_date)

        # Generar sugerencias de mejora
        suggestions = _generate_suggestions(model_stats, error_analysis)

        return {
            "period_days": days,
            "analyzed_at": datetime.now().isoformat(),
            "model_performance": model_stats,
            "trends": trends,
            "error_analysis": error_analysis,
            "suggestions": suggestions,
            "summary": {
                "total_feedback": sum(
                    m["total_feedback"] for m in model_stats.values()
                ),
                "best_model": (
                    max(model_stats.keys(), key=lambda x: model_stats[x]["avg_rating"])
                    if model_stats
                    else None
                ),
                "worst_model": (
                    min(model_stats.keys(), key=lambda x: model_stats[x]["avg_rating"])
                    if model_stats
                    else None
                ),
            },
        }


def _analyze_error_patterns(
    conn: sqlite3.Connection, cutoff_date: datetime
) -> Dict[str, Any]:
    """Analiza patrones de error en el feedback."""
    c = conn.cursor()

    # Comentarios que mencionan problemas específicos
    error_patterns = {
        "wrong_model": [
            "equivocado",
            "mal modelo",
            "tocaba",
            "debía ser",
            "wrong model",
        ],
        "too_slow": ["lento", "slow", "demasiado tiempo", "esperar"],
        "poor_quality": ["malo", "pobre", "inútil", "basura", "terrible"],
        "incomplete": ["incompleto", "falta", "inacabado", "corto"],
        "off_topic": ["tema", "irrelevante", "off topic", "no responde"],
    }

    analysis = {}

    for error_type, keywords in error_patterns.items():
        placeholders = " OR ".join(["f.comment LIKE ?" for _ in keywords])

        c.execute(
            f"""
            SELECT f.model_used, COUNT(*) as count
            FROM feedback f
            WHERE f.created_at >= ?
              AND f.rating <= 3
              AND ({placeholders})
            GROUP BY f.model_used
        """,
            (cutoff_date, *(f"%{kw}%" for kw in keywords)),
        )

        analysis[error_type] = {row[0]: row[1] for row in c.fetchall()}

    return analysis


def _generate_suggestions(
    model_stats: Dict[str, Any], error_analysis: Dict[str, Any]
) -> List[str]:
    """Genera sugerencias de mejora basadas en el análisis."""
    suggestions: List[str] = []

    if not model_stats:
        return ["No hay suficiente feedback para generar sugerencias."]

    # Encontrar el mejor y peor modelo
    best_model = max(model_stats.keys(), key=lambda x: model_stats[x]["avg_rating"])
    worst_model = min(model_stats.keys(), key=lambda x: model_stats[x]["avg_rating"])

    # Sugerencias basadas en rendimiento
    if model_stats[best_model]["avg_rating"] > 4.0:
        suggestions.append(
            f"🎯 {best_model} está funcionando excelente (rating: {model_stats[best_model]['avg_rating']})"
        )

    if model_stats[worst_model]["avg_rating"] < 3.0:
        suggestions.append(
            f"⚠️  {worst_model} necesita mejora urgente (rating: {model_stats[worst_model]['avg_rating']})"
        )

    # Sugerencias basadas en errores
    for error_type, models in error_analysis.items():
        if models:
            worst_performing = max(models.keys(), key=lambda x: models[x])
            suggestions.append(
                f"🔧 Alto {error_type.replace('_', ' ')} en {worst_performing} ({models[worst_performing]} casos)"
            )

    # Sugerencias generales
    total_feedback = sum(m["total_feedback"] for m in model_stats.values())
    if total_feedback < 10:
        suggestions.append(
            "📊 Necesitas más feedback (mínimo 10 evaluaciones) para análisis confiable"
        )

    # Balance de carga
    if len(model_stats) > 1:
        ratings = [m["avg_rating"] for m in model_stats.values()]
        if max(ratings) - min(ratings) > 1.0:
            suggestions.append(
                "⚖️  Gran diferencia de calidad entre modelos - considera rebalancear prioridades"
            )

    return suggestions


def get_recent_feedback(limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene los feedback más recientes."""
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT f.id, f.message_id, f.session_id, f.rating, f.comment, f.model_used, f.created_at,
                   m.message as original_message
            FROM feedback f
            JOIN messages m ON f.message_id = m.id
            ORDER BY f.created_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        feedback_list = []
        for row in c.fetchall():
            fid, mid, sid, rating, comment, model, created_at, original_msg = row
            feedback_list.append(
                {
                    "feedback_id": fid,
                    "message_id": mid,
                    "session_id": sid,
                    "rating": rating,
                    "comment": comment,
                    "model_used": model,
                    "created_at": created_at,
                    "original_message": (
                        original_msg[:100] + "..."
                        if len(original_msg) > 100
                        else original_msg
                    ),
                }
            )

        return feedback_list
