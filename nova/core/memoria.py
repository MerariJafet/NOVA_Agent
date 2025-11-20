import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Optional
import os

from utils.logging import get_logger
from config.settings import settings

logger = get_logger("core.memoria")


@contextmanager
def _get_conn():
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()


def init_db() -> None:
    """Create DB and tables if they don't exist."""
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model_used TEXT,
                routing_decision TEXT,
                routing_confidence INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # ensure routing_confidence column exists (migrations)
        c.execute("PRAGMA table_info(messages)")
        cols = [r[1] for r in c.fetchall()]
        if "routing_confidence" not in cols:
            try:
                c.execute("ALTER TABLE messages ADD COLUMN routing_confidence INTEGER")
            except Exception:
                pass

        # feedback table
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                session_id TEXT,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(message_id) REFERENCES messages(id)
            )
            """
        )
    logger.info("db_initialized", path=settings.db_path)


def save_conversation(
    session_id: str,
    role: str,
    content: str,
    model_used: Optional[str] = None,
    routing_decision: Optional[str] = None,
    routing_confidence: Optional[int] = None,
) -> int:
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO messages (session_id, role, content, model_used, routing_decision, routing_confidence) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, role, content, model_used, routing_decision, routing_confidence),
        )
        last_id = c.lastrowid
    logger.info("message_saved", session_id=session_id, role=role, message_id=last_id)
    return last_id


def get_conversation(session_id: str, limit: int = 20) -> List[Dict]:
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, session_id, role, content, model_used, routing_decision, created_at FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        rows = c.fetchall()
    result = [
        {
            "id": r[0],
            "session_id": r[1],
            "role": r[2],
            "content": r[3],
            "model_used": r[4],
            "routing_decision": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]
    logger.info("conversation_retrieved", session_id=session_id, count=len(result))
    return result


def search_messages(keyword: str, limit: int = 50) -> List[Dict]:
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, session_id, role, content FROM messages WHERE content LIKE ? LIMIT ?", (f"%{keyword}%", limit))
        rows = c.fetchall()
    result = [
        {"id": r[0], "session_id": r[1], "role": r[2], "content": r[3]} for r in rows
    ]
    logger.info("search_messages", keyword=keyword, found=len(result))
    return result
