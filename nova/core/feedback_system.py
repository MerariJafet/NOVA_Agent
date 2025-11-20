from typing import Dict, Any, Optional
from nova.core import memoria
from utils.logging import get_logger
from config import model_profiles as profiles

logger = get_logger("core.feedback")


def record_feedback(message_id: int, session_id: str, rating: int, comment: Optional[str] = None) -> int:
    """Store a feedback entry linked to a message_id."""
    # Basic validation
    if rating < 1 or rating > 5:
        raise ValueError("rating must be 1-5")
    with memoria._get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO feedback (message_id, session_id, rating, comment) VALUES (?, ?, ?, ?)",
            (message_id, session_id, rating, comment),
        )
        fid = c.lastrowid
    logger.info("feedback_recorded", feedback_id=fid, message_id=message_id, session_id=session_id, rating=rating)
    return fid


def analyze_performance() -> Dict[str, Any]:
    """Return simple metrics: per-model avg rating and counts."""
    with memoria._get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT m.model_used, AVG(f.rating) as avg_rating, COUNT(f.id) as feedback_count FROM feedback f JOIN messages m ON f.message_id = m.id GROUP BY m.model_used"
        )
        rows = c.fetchall()
    result = {r[0]: {"avg_rating": r[1], "feedback_count": r[2]} for r in rows}
    logger.info("performance_analyzed", result=result)
    return result


def suggest_improvements(threshold: float = 3.5) -> Dict[str, Any]:
    perf = analyze_performance()
    suggestions = {}
    for model, data in perf.items():
        if data.get("avg_rating") is not None and data["avg_rating"] < threshold:
            # find alternative highest priority model from profiles
            alts = list(profiles._DATA.keys())
            suggestions[model] = {"avg_rating": data["avg_rating"], "suggested_alternatives": alts}
    logger.info("suggestions_generated", suggestions=suggestions)
    return suggestions
