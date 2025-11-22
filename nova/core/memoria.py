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

        # Tabla response_cache para Sprint 3 Día 3 - Caché Inteligente
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS response_cache (
                cache_key TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                model_name TEXT NOT NULL,
                response TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                hit_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Migrar datos de tabla antigua si existe
        try:
            c.execute("PRAGMA table_info(response_cache)")
            cols = [r[1] for r in c.fetchall()]

            # Si tiene la estructura antigua, migrar datos
            if "query_text" in cols and "cache_key" not in cols:
                logger.info("migrating_cache_table")
                # Crear nueva tabla temporal
                c.execute("""
                    CREATE TABLE response_cache_new (
                        cache_key TEXT PRIMARY KEY,
                        query_hash TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        response TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL,
                        hit_count INTEGER DEFAULT 0,
                        last_accessed REAL NOT NULL,
                        metadata TEXT
                    )
                """)

                # Migrar datos existentes
                import time
                import hashlib
                import json

                c.execute("SELECT query_text, response_text, model_used, created_at FROM response_cache")
                old_rows = c.fetchall()

                for row in old_rows:
                    query_text, response_text, model_used, created_at = row
                    # Generar cache_key y otros campos
                    cache_key = hashlib.sha256(f"{query_text}{model_used}".encode()).hexdigest()
                    query_hash = hashlib.md5(query_text.encode()).hexdigest()
                    created_timestamp = time.mktime(time.strptime(created_at, "%Y-%m-%d %H:%M:%S")) if isinstance(created_at, str) else time.time()
                    expires_at = created_timestamp + (7 * 24 * 60 * 60)  # 7 días TTL

                    response_json = json.dumps({"text": response_text})
                    metadata_json = json.dumps({"migrated": True, "old_created_at": created_at})

                    c.execute("""
                        INSERT INTO response_cache_new
                        (cache_key, query_hash, model_name, response, created_at, expires_at, hit_count, last_accessed, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (cache_key, query_hash, model_used, response_json, created_timestamp, expires_at, 0, created_timestamp, metadata_json))

                # Reemplazar tabla
                c.execute("DROP TABLE response_cache")
                c.execute("ALTER TABLE response_cache_new RENAME TO response_cache")
                logger.info("cache_migration_completed")

        except Exception as e:
            logger.warning("cache_migration_failed", error=str(e))

        # Tabla optimization_log para auto-optimización
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

        # Índices para performance
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback(message_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at)")
            # Índices para caché inteligente
            c.execute("CREATE INDEX IF NOT EXISTS idx_response_cache_expires_at ON response_cache(expires_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_response_cache_model ON response_cache(model_name)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_response_cache_query_model ON response_cache(query, model_name)")
            # Índices para optimization_log
            c.execute("CREATE INDEX IF NOT EXISTS idx_optimization_model ON optimization_log(model_name)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_optimization_created ON optimization_log(created_at)")
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
