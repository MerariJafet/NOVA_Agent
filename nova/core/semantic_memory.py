import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.logging import get_logger

logger = get_logger("core.semantic_memory")


class SemanticMemory:
    """Sistema de memoria semántica usando ChromaDB y embeddings."""

    def __init__(self):
        self.db_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db"
        )
        os.makedirs(self.db_path, exist_ok=True)
        self.available = True
        self._model = None
        self._chromadb = None
        self._SentenceTransformer = None

        # Cargar dependencias en tiempo de ejecución para evitar fallos por falta de paquetes
        try:
            import chromadb  # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._chromadb = chromadb
            self._SentenceTransformer = SentenceTransformer

            # Inicializar ChromaDB
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.collection = self.client.get_or_create_collection("messages")
            logger.info("semantic_memory_initialized", db_path=self.db_path)
        except Exception as e:
            # Si faltan dependencias o hay error de inicialización, marcar como no disponible
            self.available = False
            self.client = None
            self.collection = None
            logger.error("semantic_memory_unavailable", error=str(e))

    def generate_embedding(self, text: str) -> List[float]:
        """Genera embedding para un texto."""
        if not self._ensure_ready():
            return []
        try:
            self._ensure_model_loaded()
            if not self._model:
                return []
            embedding = self._model.encode(text).tolist()
            return embedding
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            return []

    def _ensure_ready(self) -> bool:
        """Verifica si la memoria semántica está disponible."""
        if not self.available or not self.collection:
            logger.warning("semantic_memory_not_ready")
            return False
        return True

    def _ensure_model_loaded(self) -> None:
        """Carga el modelo de embeddings si aún no está cargado."""
        if self._model or not self._SentenceTransformer:
            return
        try:
            self._model = self._SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.error("semantic_model_load_failed", error=str(e))
            self.available = False

    def add_message(
        self,
        message_id: int,
        content: str,
        session_id: str,
        role: str,
        model_used: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> bool:
        """Agrega un mensaje a la memoria semántica."""
        if not self._ensure_ready():
            return False
        try:
            # Generar embedding
            embedding = self.generate_embedding(content)
            if not embedding:
                return False

            # Metadata
            metadata = {
                "session_id": session_id,
                "role": role,
                "model_used": model_used or "",
                "created_at": created_at or datetime.now().isoformat(),
                "content_length": len(content),
            }

            # ID único para ChromaDB
            chroma_id = f"{session_id}_{message_id}_{role}"

            # Agregar a colección
            self.collection.add(
                ids=[chroma_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[content],
            )

            logger.info(
                "message_added_to_semantic_memory",
                message_id=message_id,
                session_id=session_id,
                role=role,
            )
            return True

        except Exception as e:
            logger.error(
                "add_message_failed",
                error=str(e),
                message_id=message_id,
                session_id=session_id,
            )
            return False

    def search_similar(
        self,
        query: str,
        n_results: int = 10,
        session_id: Optional[str] = None,
        min_similarity: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Busca mensajes similares por semántica."""
        if not self._ensure_ready():
            return []
        try:
            # Generar embedding de la query
            query_embedding = self.generate_embedding(query)
            if not query_embedding:
                return []

            # Filtros
            where = None
            if session_id:
                where = {"session_id": session_id}

            # Buscar
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["metadatas", "documents", "distances"],
            )

            # Procesar resultados
            processed_results = []
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    similarity = 1 - distance  # ChromaDB usa distancia coseno

                    # Filtrar por similitud mínima
                    if similarity >= min_similarity:
                        metadata = results["metadatas"][0][i]
                        processed_results.append(
                            {
                                "id": doc_id,
                                "content": results["documents"][0][i],
                                "metadata": metadata,
                                "similarity": round(similarity, 3),
                                "distance": round(distance, 3),
                            }
                        )

            # Ordenar por similitud descendente
            processed_results.sort(key=lambda x: x["similarity"], reverse=True)

            logger.info(
                "semantic_search_completed",
                query_length=len(query),
                results_found=len(processed_results),
                session_id=session_id,
            )
            return processed_results

        except Exception as e:
            logger.error("search_similar_failed", error=str(e), query=query[:50])
            return []

    def get_relevant_context(
        self, query: str, n_results: int = 5, session_id: Optional[str] = None
    ) -> str:
        """Obtiene contexto relevante para una query."""
        if not self._ensure_ready():
            return ""
        try:
            results = self.search_similar(
                query, n_results, session_id, min_similarity=0.3
            )

            if not results:
                return ""

            # Formatear como contexto
            context_parts = []
            for result in results[:n_results]:
                metadata = result["metadata"]
                role = metadata.get("role", "unknown")
                content = result["content"]
                similarity = result["similarity"]

                context_parts.append(f"[{role.upper()}] {content} (sim: {similarity})")

            context = "\n".join(context_parts)
            logger.info("relevant_context_generated", context_length=len(context))
            return context

        except Exception as e:
            logger.error("get_relevant_context_failed", error=str(e))
            return ""

    def sync_from_sqlite(self) -> bool:
        """Sincroniza mensajes desde SQLite (placeholder para implementación futura)."""
        if not self.available:
            return False
        try:
            # Por ahora, solo loggear
            logger.info("sync_from_sqlite_started")
            # TODO: Implementar sincronización desde tabla messages
            logger.info("sync_from_sqlite_completed")
            return True
        except Exception as e:
            logger.error("sync_from_sqlite_failed", error=str(e))
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la memoria semántica."""
        if not self.available or not self.collection:
            return {
                "error": "Semantic memory unavailable. Install chromadb and sentence-transformers.",
                "total_messages": 0,
            }
        try:
            count = self.collection.count()
            return {
                "total_messages": count,
                "collection_name": "messages",
                "db_path": self.db_path,
                "model_name": "all-MiniLM-L6-v2",
            }
        except Exception as e:
            logger.error("get_stats_failed", error=str(e))
            return {"error": str(e)}

    def reset(self) -> bool:
        """Resetea la colección (borra todo)."""
        if not self._ensure_ready():
            return False
        try:
            self.client.delete_collection("messages")
            self.collection = self.client.create_collection("messages")
            logger.info("semantic_memory_reset")
            return True
        except Exception as e:
            logger.error("reset_failed", error=str(e))
            return False


# Instancia global
_semantic_memory_instance = None


def get_semantic_memory() -> SemanticMemory:
    global _semantic_memory_instance
    if _semantic_memory_instance is None:
        _semantic_memory_instance = SemanticMemory()
    return _semantic_memory_instance
