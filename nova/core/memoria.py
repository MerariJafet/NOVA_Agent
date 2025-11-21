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

        # Tabla messages actualizada
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                model_used TEXT,
                reasoning TEXT,
                confidence INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Migraciones para messages
        c.execute("PRAGMA table_info(messages)")
        cols = [r[1] for r in c.fetchall()]

        # Renombrar content -> message si existe la columna antigua
        if "content" in cols and "message" not in cols:
            try:
                c.execute("ALTER TABLE messages RENAME COLUMN content TO message")
            except Exception:
                pass

        # Añadir columnas faltantes
        columns_to_add = [
            ("reasoning", "TEXT"),
            ("confidence", "INTEGER")
        ]
        for col_name, col_type in columns_to_add:
            if col_name not in cols:
                try:
                    c.execute(f"ALTER TABLE messages ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        # Tabla feedback mejorada
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                session_id TEXT,
                rating INTEGER NOT NULL,
                comment TEXT,
                model_used TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(message_id) REFERENCES messages(id)
            )
            """
        )

        # Migración para feedback - añadir model_used si no existe
        c.execute("PRAGMA table_info(feedback)")
        feedback_cols = [r[1] for r in c.fetchall()]
        if "model_used" not in feedback_cols:
            try:
                c.execute("ALTER TABLE feedback ADD COLUMN model_used TEXT")
            except Exception:
                pass

        # Tabla response_cache para Sprint 3 Día 3
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS response_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT UNIQUE NOT NULL,
                query_text TEXT NOT NULL,
                response_text TEXT NOT NULL,
                model_used TEXT NOT NULL,
                confidence INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1
            )
            """
        )

        # Índices para performance
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback(message_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_cache_query ON response_cache(query_hash)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_cache_accessed ON response_cache(last_accessed)")
        except Exception:
            pass

    logger.info("db_initialized", path=settings.db_path)


def save_conversation(
    session_id: str,
    role: str,
    message: str,
    model_used: Optional[str] = None,
    reasoning: Optional[str] = None,
    confidence: Optional[int] = None,
) -> int:
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO messages (session_id, role, message, model_used, reasoning, confidence) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, role, message, model_used, reasoning, confidence),
        )
        last_id = c.lastrowid
    logger.info("message_saved", session_id=session_id, role=role, message_id=last_id)
    return last_id


def get_conversation(session_id: str, limit: int = 20) -> List[Dict]:
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, session_id, role, message, model_used, reasoning, confidence, created_at FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        rows = c.fetchall()
    result = [
        {
            "id": r[0],
            "session_id": r[1],
            "role": r[2],
            "message": r[3],
            "model_used": r[4],
            "reasoning": r[5],
            "confidence": r[6],
            "created_at": r[7],
        }
        for r in rows
    ]
    logger.info("conversation_retrieved", session_id=session_id, count=len(result))
    return result


def search_messages(keyword: str, limit: int = 50) -> List[Dict]:
    with _get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, session_id, role, message FROM messages WHERE message LIKE ? LIMIT ?", (f"%{keyword}%", limit))
        rows = c.fetchall()
    result = [
        {"id": r[0], "session_id": r[1], "role": r[2], "message": r[3]} for r in rows
    ]
    logger.info("search_messages", keyword=keyword, found=len(result))
    return result
