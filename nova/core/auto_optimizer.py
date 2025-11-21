"""
Auto Optimizer - Sprint 3 Día 2
Sistema de auto-optimización automática que ajusta prioridades de modelos basado en feedback humano.
"""
import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from nova.core.feedback_system import analyze_performance
from nova.core.memoria import _get_conn
from config.settings import settings
from utils.logging import get_logger

logger = get_logger("core.auto_optimizer")


def _init_optimization_log() -> None:
    """Crear tabla optimization_log si no existe."""
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS optimization_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                old_priority INTEGER NOT NULL,
                new_priority INTEGER NOT NULL,
                change_amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                avg_rating REAL,
                total_feedback INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Índice para performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_optimization_model ON optimization_log(model_name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_optimization_created ON optimization_log(created_at)")


def _load_model_profiles() -> Dict[str, Any]:
    """Cargar perfiles de modelos desde el archivo JSON."""
    try:
        with open(settings.model_profiles_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error("load_model_profiles_failed", error=str(e))
        raise


def _save_model_profiles(profiles: Dict[str, Any]) -> None:
    """Guardar perfiles de modelos en el archivo JSON."""
    try:
        with open(settings.model_profiles_path, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
        logger.info("model_profiles_saved", path=settings.model_profiles_path)
    except Exception as e:
        logger.error("save_model_profiles_failed", error=str(e))
        raise


def _backup_model_profiles() -> str:
    """Crear backup del archivo model_profiles.json."""
    backup_dir = Path(settings.model_profiles_path).parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"model_profiles_{timestamp}.json"

    shutil.copy2(settings.model_profiles_path, backup_path)
    logger.info("model_profiles_backup_created", backup_path=str(backup_path))
    return str(backup_path)


def _log_optimization(model_name: str, old_priority: int, new_priority: int,
                     change_amount: int, reason: str, avg_rating: float = None,
                     total_feedback: int = None) -> None:
    """Registrar cambio de optimización en la base de datos."""
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO optimization_log
            (model_name, old_priority, new_priority, change_amount, reason, avg_rating, total_feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (model_name, old_priority, new_priority, change_amount, reason, avg_rating, total_feedback)
        )
        log_id = c.lastrowid
        logger.info("optimization_logged", log_id=log_id, model=model_name, change=change_amount)


def auto_optimize(max_change: int = 20, min_feedback: int = 5) -> Dict[str, Any]:
    """
    Auto-optimización automática basada en feedback humano.

    Args:
        max_change: Cambio máximo de priority por ejecución (±20 por defecto)
        min_feedback: Mínimo de evaluaciones requeridas para optimizar un modelo

    Returns:
        Dict con resultados de la optimización
    """
    logger.info("auto_optimize_start", max_change=max_change, min_feedback=min_feedback)

    try:
        # Inicializar tabla de logs si no existe
        _init_optimization_log()

        # Analizar rendimiento reciente (últimos 7 días)
        performance = analyze_performance(days=7)

        if not performance.get("model_performance"):
            logger.warning("auto_optimize_no_performance_data")
            return {
                "status": "no_data",
                "message": "No hay datos de rendimiento suficientes para optimizar",
                "changes_applied": []
            }

        # Cargar perfiles actuales
        model_profiles = _load_model_profiles()

        # Crear backup antes de modificar
        backup_path = _backup_model_profiles()

        # Calcular y aplicar cambios
        changes_applied = []
        total_feedback = performance["summary"]["total_feedback"]

        for model_name, stats in performance["model_performance"].items():
            if stats["total_feedback"] < min_feedback:
                logger.debug("model_skipped_insufficient_feedback",
                           model=model_name, feedback=stats["total_feedback"], required=min_feedback)
                continue

            if model_name not in model_profiles:
                logger.warning("model_not_in_profiles", model=model_name)
                continue

            # Calcular ajuste basado en rating
            # Rating 3.0 = baseline (sin cambio)
            # Cada 0.5 puntos de rating = ±10 priority
            # Ej: rating 4.0 → +20 priority, rating 2.0 → -20 priority
            rating_diff = stats["avg_rating"] - 3.0
            raw_change = rating_diff * 20  # 0.5 rating = 10 priority

            # Aplicar límite máximo de cambio
            change_amount = max(-max_change, min(max_change, int(raw_change)))

            # Calcular nueva priority
            old_priority = model_profiles[model_name]["priority"]
            new_priority = max(1, min(100, old_priority + change_amount))  # Clamp entre 1-100

            # Solo aplicar si hay cambio real
            if new_priority != old_priority:
                # Actualizar perfil
                model_profiles[model_name]["priority"] = new_priority

                # Registrar cambio
                reason = f"Auto-optimización: rating {stats['avg_rating']:.1f} ({stats['total_feedback']} evaluaciones)"
                _log_optimization(
                    model_name=model_name,
                    old_priority=old_priority,
                    new_priority=new_priority,
                    change_amount=change_amount,
                    reason=reason,
                    avg_rating=stats["avg_rating"],
                    total_feedback=stats["total_feedback"]
                )

                changes_applied.append({
                    "model": model_name,
                    "old_priority": old_priority,
                    "new_priority": new_priority,
                    "change": change_amount,
                    "reason": reason
                })

                logger.info("priority_adjusted",
                          model=model_name,
                          old=old_priority,
                          new=new_priority,
                          change=change_amount,
                          rating=stats["avg_rating"])

        # Guardar cambios si hay actualizaciones
        if changes_applied:
            _save_model_profiles(model_profiles)
            logger.info("auto_optimize_completed",
                      changes=len(changes_applied),
                      total_feedback=total_feedback,
                      backup=backup_path)

            return {
                "status": "optimized",
                "changes_applied": changes_applied,
                "total_feedback_analyzed": total_feedback,
                "backup_created": backup_path,
                "model_profiles_updated": True
            }
        else:
            logger.info("auto_optimize_no_changes_needed")
            return {
                "status": "no_changes",
                "message": "No se requieren cambios de optimización",
                "changes_applied": [],
                "total_feedback_analyzed": total_feedback
            }

    except Exception as e:
        logger.error("auto_optimize_failed", error=str(e))
        return {
            "status": "error",
            "message": f"Error en auto-optimización: {str(e)}",
            "changes_applied": []
        }


def get_optimization_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Obtener historial de optimizaciones."""
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT model_name, old_priority, new_priority, change_amount, reason,
                   avg_rating, total_feedback, created_at
            FROM optimization_log
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )

        history = []
        for row in c.fetchall():
            history.append({
                "model_name": row[0],
                "old_priority": row[1],
                "new_priority": row[2],
                "change_amount": row[3],
                "reason": row[4],
                "avg_rating": row[5],
                "total_feedback": row[6],
                "created_at": row[7]
            })

        return history


def get_current_priorities() -> Dict[str, int]:
    """Obtener prioridades actuales de todos los modelos."""
    try:
        profiles = _load_model_profiles()
        return {model: data["priority"] for model, data in profiles.items()}
    except Exception as e:
        logger.error("get_current_priorities_failed", error=str(e))
        return {}