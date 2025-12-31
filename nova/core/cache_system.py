#!/usr/bin/env python3
"""
Sistema de Caché Inteligente para NOVA
Implementa caché de respuestas con TTL, hit counting y invalidación automática
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any
import os
import threading

from nova.core.memoria import _get_conn
from config.settings import settings


class CacheSystem:
    """Sistema de caché inteligente para respuestas de modelos"""

    def __init__(self, ttl_days: int = 7):
        self.ttl_seconds = ttl_days * 24 * 60 * 60
        self._init_cache_table()

    def _init_cache_table(self):
        """Inicializar tabla de caché si no existe"""
        with _get_conn() as conn:
            conn.execute(
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

            # Índices para performance
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_response_cache_expires_at
                ON response_cache(expires_at)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_response_cache_model
                ON response_cache(model_name)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_response_cache_query_model
                ON response_cache(query, model_name)
            """
            )

            conn.commit()

    def _generate_cache_key(self, query: str, model_name: str, **kwargs) -> str:
        """Generar clave única para el caché"""
        # Incluir parámetros relevantes en el hash
        cache_data = {
            "query": query.strip().lower(),
            "model": model_name,
            "params": {
                k: v
                for k, v in kwargs.items()
                if k in ["temperature", "max_tokens", "top_p"]
            },
        }

        # Crear hash consistente
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()

    def get_cached_response(
        self, query: str, model_name: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener respuesta del caché si existe y no ha expirado

        Returns:
            Dict con respuesta y metadata, o None si no hay cache
        """
        cache_key = self._generate_cache_key(query, model_name, **kwargs)
        current_time = time.time()

        with _get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT response, created_at, hit_count, metadata
                FROM response_cache
                WHERE cache_key = ? AND expires_at > ?
            """,
                (cache_key, current_time),
            )

            row = cursor.fetchone()

            if row:
                response_json, created_at, hit_count, metadata_json = row

                # Actualizar hit_count y last_accessed
                new_hit_count = hit_count + 1
                conn.execute(
                    """
                    UPDATE response_cache
                    SET hit_count = ?, last_accessed = ?
                    WHERE cache_key = ?
                """,
                    (new_hit_count, current_time, cache_key),
                )
                conn.commit()

                # Parsear respuesta
                try:
                    response_data = json.loads(response_json)
                    metadata = json.loads(metadata_json) if metadata_json else {}

                    return {
                        "response": response_data,
                        "cached": True,
                        "cache_key": cache_key,
                        "created_at": created_at,
                        "hit_count": new_hit_count,
                        "latency": 0,  # Cache hit = ~0ms
                        "metadata": metadata,
                    }
                except json.JSONDecodeError:
                    # Si hay error en el JSON, eliminar entrada corrupta
                    conn.execute(
                        "DELETE FROM response_cache WHERE cache_key = ?", (cache_key,)
                    )
                    conn.commit()
                    return None

        return None

    def save_to_cache(
        self,
        query: str,
        model_name: str,
        response: Any,
        metadata: Optional[Dict] = None,
        **kwargs,
    ) -> str:
        """
        Guardar respuesta en el caché

        Args:
            query: La consulta original
            model_name: Nombre del modelo usado
            response: Respuesta a cachear
            metadata: Información adicional (tiempo de respuesta, etc.)
            **kwargs: Parámetros adicionales para la clave

        Returns:
            La cache_key generada
        """
        cache_key = self._generate_cache_key(query, model_name, **kwargs)
        current_time = time.time()
        expires_at = current_time + self.ttl_seconds

        # Serializar respuesta
        if isinstance(response, dict):
            response_json = json.dumps(response)
        else:
            response_json = json.dumps({"text": str(response)})

        metadata_json = json.dumps(metadata or {})

        with _get_conn() as conn:
            # Insertar o reemplazar
            conn.execute(
                """
                INSERT OR REPLACE INTO response_cache
                (cache_key, query, model_name, response, metadata, expires_at, hit_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    cache_key,
                    query,  # Guardar la query completa
                    model_name,
                    response_json,
                    metadata_json,
                    expires_at,
                    0,  # hit_count inicia en 0
                ),
            )
            conn.commit()

        return cache_key

    def invalidate_cache(
        self, pattern: Optional[str] = None, model_name: Optional[str] = None
    ) -> int:
        """
        Invalidar entradas del caché

        Args:
            pattern: Patrón para buscar en query (opcional)
            model_name: Invalidar solo para un modelo específico (opcional)

        Returns:
            Número de entradas invalidadas
        """
        with _get_conn() as conn:
            if model_name:
                # Invalidar por modelo
                cursor = conn.execute(
                    "DELETE FROM response_cache WHERE model_name = ?", (model_name,)
                )
            elif pattern:
                # Invalidar por patrón en query
                cursor = conn.execute(
                    "DELETE FROM response_cache WHERE query LIKE ?", (f"%{pattern}%",)
                )
            else:
                # Invalidar todo el caché
                cursor = conn.execute("DELETE FROM response_cache")

            deleted_count = cursor.rowcount
            conn.commit()

        return deleted_count

    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del caché"""
        current_time = time.time()

        with _get_conn() as conn:
            # Total de entradas
            cursor = conn.execute("SELECT COUNT(*) FROM response_cache")
            total_entries = cursor.fetchone()[0]

            # Entradas válidas (no expiradas)
            cursor = conn.execute(
                "SELECT COUNT(*) FROM response_cache WHERE expires_at > ?",
                (current_time,),
            )
            valid_entries = cursor.fetchone()[0]

            # Entradas expiradas
            expired_entries = total_entries - valid_entries

            # Total de hits
            cursor = conn.execute("SELECT SUM(hit_count) FROM response_cache")
            total_hits = cursor.fetchone()[0] or 0

            # Hit rate (si hay entradas válidas)
            hit_rate = (
                (total_hits / max(total_entries, 1)) * 100 if total_entries > 0 else 0
            )

            # Tamaño aproximado (bytes)
            cursor = conn.execute("SELECT SUM(LENGTH(response)) FROM response_cache")
            size_bytes = cursor.fetchone()[0] or 0

            # Modelo más usado en caché
            cursor = conn.execute(
                """
                SELECT model_name, COUNT(*) as count
                FROM response_cache
                GROUP BY model_name
                ORDER BY count DESC
                LIMIT 1
            """
            )
            top_model_row = cursor.fetchone()
            top_model = top_model_row[0] if top_model_row else "Ninguno"

        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "total_hits": total_hits,
            "hit_rate_percent": round(hit_rate, 2),
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "top_model": top_model,
            "ttl_days": self.ttl_seconds / (24 * 60 * 60),
        }

    def get_cache_hit_rate(self) -> float:
        """Obtener hit rate actual del caché"""
        stats = self.get_cache_stats()
        return stats["hit_rate_percent"]

    def start_model_profiles_monitor(self):
        """Iniciar monitoreo de cambios en model_profiles.json"""

        def monitor_thread():
            last_mtime = 0
            while True:
                try:
                    if os.path.exists(settings.model_profiles_path):
                        current_mtime = os.path.getmtime(settings.model_profiles_path)
                        if current_mtime > last_mtime and last_mtime > 0:
                            # Archivo cambió - invalidar caché
                            invalidated = self.invalidate_cache()
                            print(
                                f"🔄 Model profiles cambió - {invalidated} entradas de caché invalidadas"
                            )

                        last_mtime = current_mtime

                except Exception as e:
                    print(f"⚠️ Error monitoreando model_profiles: {e}")

                time.sleep(5)  # Verificar cada 5 segundos

        # Iniciar thread en background
        monitor = threading.Thread(target=monitor_thread, daemon=True)
        monitor.start()
        print("👀 Monitoreo de model_profiles.json iniciado")


# Instancia global del sistema de caché
cache_system = CacheSystem(ttl_days=7)

# Iniciar monitoreo automático de model_profiles.json
cache_system.start_model_profiles_monitor()
