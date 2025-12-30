"""
Sistema de memoria episódica para NOVA.
Extrae y almacena hechos sobre los usuarios de sus conversaciones.
"""

import re
from typing import List, Dict, Any, Optional
from utils.logging import get_logger

logger = get_logger("core.episodic_memory")


class EpisodicMemory:
    """Sistema de memoria episódica que extrae hechos de conversaciones."""

    def __init__(self):
        pass

    def extract_facts(self, message: str) -> List[Dict[str, Any]]:
        """
        Extrae hechos de un mensaje de texto.

        Args:
            message: Mensaje del usuario

        Returns:
            Lista de hechos extraídos
        """
        facts = []
        message_lower = message.lower()

        # Patrones de extracción de hechos
        patterns = {
            'name': [
                r'me llamo ([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)',
                r'mi nombre es ([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)',
                r'soy ([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)',
            ],
            'age': [
                r'tengo (\d+) años',
                r'tengo (\d+) años de edad',
            ],
            'employer': [
                r'trabajo en ([A-Za-zÁÉÍÓÚáéíóúñÑ\s&]+)',
                r'trabajo para ([A-Za-zÁÉÍÓÚáéíóúñÑ\s&]+)',
            ],
            'job_title': [
                r'trabajo como ([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)',
                r'soy ([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+) de profesión',
                r'mi profesión es ([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)',
            ],
            'likes': [
                r'me gusta ([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)',
                r'me encantan? ([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)',
            ],
            'location': [
                r'vivo en ([A-Za-zÁÉÍÓÚáéíóúñÑ\s,]+)',
                r'estoy en ([A-Za-zÁÉÍÓÚáéíóúñÑ\s,]+)',
                r'mi ubicación es ([A-Za-zÁÉÍÓÚáéíóúñÑ\s,]+)',
            ]
        }

        for fact_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, message_lower, re.IGNORECASE)
                for match in matches:
                    # Limpiar el match
                    value = match.strip()
                    if value:
                        # Crear clave única para el hecho
                        fact_key = f"{fact_type}_{value.lower().replace(' ', '_').replace(',', '')}"

                        facts.append({
                            'fact_type': fact_type,
                            'fact_key': fact_key,
                            'fact_value': value,
                            'confidence': 1.0
                        })

        logger.info("facts_extracted", message_length=len(message), facts_found=len(facts))
        return facts

    def save_fact(self, session_id: str, fact: Dict[str, Any]) -> bool:
        """
        Guarda un hecho en la base de datos.

        Args:
            session_id: ID de la sesión
            fact: Diccionario con los datos del hecho

        Returns:
            True si se guardó correctamente
        """
        try:
            from nova.core.memoria import _get_conn

            with _get_conn() as conn:
                c = conn.cursor()

                # Verificar si existe la tabla facts
                c.execute("""
                    CREATE TABLE IF NOT EXISTS facts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        fact_type TEXT NOT NULL,
                        fact_key TEXT NOT NULL UNIQUE,
                        fact_value TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Intentar insertar, si ya existe actualizar
                c.execute("""
                    INSERT OR REPLACE INTO facts
                    (session_id, fact_type, fact_key, fact_value, confidence, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    session_id,
                    fact['fact_type'],
                    fact['fact_key'],
                    fact['fact_value'],
                    fact.get('confidence', 1.0)
                ))

                conn.commit()

                logger.info("fact_saved",
                           session_id=session_id,
                           fact_type=fact['fact_type'],
                           fact_key=fact['fact_key'])
                return True

        except Exception as e:
            logger.error("fact_save_failed",
                        error=str(e),
                        session_id=session_id,
                        fact_type=fact.get('fact_type'))
            return False

    def get_facts(self, session_id: str, fact_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene hechos de una sesión.

        Args:
            session_id: ID de la sesión
            fact_type: Tipo de hecho (opcional, para filtrar)

        Returns:
            Lista de hechos
        """
        try:
            from nova.core.memoria import _get_conn

            with _get_conn() as conn:
                c = conn.cursor()

                if fact_type:
                    c.execute("""
                        SELECT id, session_id, fact_type, fact_key, fact_value, confidence, created_at, updated_at
                        FROM facts
                        WHERE session_id = ? AND fact_type = ?
                        ORDER BY updated_at DESC
                    """, (session_id, fact_type))
                else:
                    c.execute("""
                        SELECT id, session_id, fact_type, fact_key, fact_value, confidence, created_at, updated_at
                        FROM facts
                        WHERE session_id = ?
                        ORDER BY updated_at DESC
                    """, (session_id,))

                rows = c.fetchall()
                facts = []
                for row in rows:
                    facts.append({
                        'id': row[0],
                        'session_id': row[1],
                        'fact_type': row[2],
                        'fact_key': row[3],
                        'fact_value': row[4],
                        'confidence': row[5],
                        'created_at': row[6],
                        'updated_at': row[7]
                    })

                return facts

        except Exception as e:
            logger.error("facts_get_failed", error=str(e), session_id=session_id)
            return []

    def delete_fact(self, fact_id: int) -> bool:
        """
        Elimina un hecho por su ID.

        Args:
            fact_id: ID del hecho

        Returns:
            True si se eliminó correctamente
        """
        try:
            from nova.core.memoria import _get_conn

            with _get_conn() as conn:
                c = conn.cursor()

                c.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
                deleted = c.rowcount > 0
                conn.commit()

                if deleted:
                    logger.info("fact_deleted", fact_id=fact_id)
                else:
                    logger.warning("fact_not_found", fact_id=fact_id)

                return deleted

        except Exception as e:
            logger.error("fact_delete_failed", error=str(e), fact_id=fact_id)
            return False

    def format_facts_for_prompt(self, session_id: str) -> str:
        """
        Formatea los hechos de una sesión para incluirlos en el prompt.

        Args:
            session_id: ID de la sesión

        Returns:
            Texto formateado con los hechos
        """
        try:
            facts = self.get_facts(session_id)

            if not facts:
                return ""

            # Organizar hechos por tipo
            facts_by_type = {}
            for fact in facts:
                fact_type = fact['fact_type']
                if fact_type not in facts_by_type:
                    facts_by_type[fact_type] = []
                facts_by_type[fact_type].append(fact)

            # Mapeo de tipos a secciones
            section_mapping = {
                'name': ('👤 Personal', 'Se llama {}'),
                'age': ('👤 Personal', 'Tiene {} años'),
                'location': ('👤 Personal', 'Vive en {}'),
                'employer': ('💼 Profesional', 'Trabaja en {}'),
                'job_title': ('💼 Profesional', 'Trabaja como {}'),
                'likes': ('⭐ Preferencias', 'Le gusta {}'),
            }

            sections = {}

            for fact_type, fact_list in facts_by_type.items():
                if fact_type in section_mapping:
                    section_name, template = section_mapping[fact_type]
                    if section_name not in sections:
                        sections[section_name] = []

                    for fact in fact_list:
                        sections[section_name].append(template.format(fact['fact_value']))

            # Construir el texto formateado
            if not sections:
                return ""

            formatted_parts = ["--- Información sobre el usuario ---"]

            for section_name, facts_text in sections.items():
                formatted_parts.append(f"{section_name}:")
                for fact_text in facts_text:
                    formatted_parts.append(f"• {fact_text}")

            formatted_parts.append("--- Fin información usuario ---")

            result = "\n".join(formatted_parts)
            logger.info("facts_formatted", session_id=session_id, facts_count=len(facts))
            return result

        except Exception as e:
            logger.error("facts_format_failed", error=str(e), session_id=session_id)
            return ""


# Instancia global
episodic_memory = EpisodicMemory()