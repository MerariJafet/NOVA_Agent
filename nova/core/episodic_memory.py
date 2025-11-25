import re
from typing import List, Dict, Optional, Any
import sqlite3

from utils.logging import get_logger
from nova.core.memoria import _get_conn

logger = get_logger("core.episodic_memory")


class EpisodicMemory:
    """Sistema de memoria episódica para almacenar y recuperar hechos del usuario."""

    def __init__(self):
        self.fact_patterns = {
            # Personal information
            'name': [
                re.compile(r'me llamo\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ]+)*)', re.IGNORECASE),
                re.compile(r'mi nombre es\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ]+)*)', re.IGNORECASE),
                re.compile(r'soy\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ]+)*)', re.IGNORECASE),
            ],
            'age': [
                re.compile(r'tengo\s+(\d{1,3})\s+años', re.IGNORECASE),
            ],
            'location': [
                re.compile(r'vivo en\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ,.-]+)*)', re.IGNORECASE),
                re.compile(r'soy de\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ,.-]+)*)', re.IGNORECASE),
            ],
            'employer': [
                re.compile(r'trabajo en\s+([A-Za-zÁÉÍÓÚáéíóúÑñ&]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ&.-]+)*)', re.IGNORECASE),
            ],
            'job_title': [
                re.compile(r'trabajo como\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ/-]+)*)', re.IGNORECASE),
                re.compile(r'soy\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ/-]+)*)', re.IGNORECASE),
            ],
            'current_project': [
                re.compile(r'estoy trabajando en\s+([A-Za-zÁÉÍÓÚáéíóúÑñ0-9]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ0-9&.-]+)*)', re.IGNORECASE),
            ],
            'likes': [
                re.compile(r'me gusta\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ,.-]+)*)', re.IGNORECASE),
                re.compile(r'me gustan\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ,.-]+)*)', re.IGNORECASE),
            ],
            'dislikes': [
                re.compile(r'no me gusta\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ,.-]+)*)', re.IGNORECASE),
            ],
        }

    def extract_facts(self, message: str, message_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extrae hechos del mensaje del usuario usando patrones regex."""
        facts = []
        message_lower = message.lower()

        for fact_type, patterns in self.fact_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(message)
                for match in matches:
                    # Limpiar el match
                    fact_value = match.strip()
                    if not fact_value:
                        continue

                    # Crear clave única para el hecho
                    fact_key = f"{fact_type}_{fact_value.lower().replace(' ', '_')}"

                    fact = {
                        'fact_type': fact_type,
                        'fact_key': fact_key,
                        'fact_value': fact_value,
                        'source_message_id': message_id,
                        'confidence': 1.0,
                        'raw_text': match.strip(),
                    }
                    facts.append(fact)
                    logger.info("fact_extracted", fact_type=fact_type, fact_value=fact_value)

        if facts:
            logger.info("facts_extracted", count=len(facts), message_id=message_id)
        return facts

    def save_fact(self, session_id: str, fact: Dict[str, Any]) -> bool:
        """Guarda un hecho en la base de datos, evitando duplicados."""
        try:
            with _get_conn() as conn:
                c = conn.cursor()

                # Verificar si ya existe un hecho con la misma clave para esta sesión
                c.execute(
                    "SELECT id, fact_value FROM facts WHERE session_id = ? AND fact_key = ?",
                    (session_id, fact['fact_key'])
                )
                existing = c.fetchone()

                if existing:
                    existing_id, existing_value = existing
                    # Si el valor cambió, actualizar
                    if existing_value != fact['fact_value']:
                        c.execute(
                            "UPDATE facts SET fact_value = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (fact['fact_value'], existing_id)
                        )
                        logger.info("fact_updated", fact_key=fact['fact_key'], old_value=existing_value, new_value=fact['fact_value'])
                    else:
                        logger.debug("fact_unchanged", fact_key=fact['fact_key'])
                    return True
                else:
                    # Insertar nuevo hecho
                    c.execute(
                        """
                        INSERT INTO facts (session_id, fact_type, fact_key, fact_value, source_message_id, confidence)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            fact['fact_type'],
                            fact['fact_key'],
                            fact['fact_value'],
                            fact.get('source_message_id'),
                            fact.get('confidence', 1.0)
                        )
                    )
                    logger.info("fact_saved", fact_key=fact['fact_key'], fact_value=fact['fact_value'])
                    return True

        except Exception as e:
            logger.error("fact_save_error", error=str(e), fact_key=fact.get('fact_key'))
            return False

    def get_facts(self, session_id: str, fact_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Recupera hechos de una sesión, opcionalmente filtrados por tipo."""
        try:
            with _get_conn() as conn:
                c = conn.cursor()

                if fact_type:
                    c.execute(
                        "SELECT id, session_id, fact_type, fact_key, fact_value, source_message_id, confidence, created_at, updated_at FROM facts WHERE session_id = ? AND fact_type = ? ORDER BY updated_at DESC LIMIT ?",
                        (session_id, fact_type, limit)
                    )
                else:
                    c.execute(
                        "SELECT id, session_id, fact_type, fact_key, fact_value, source_message_id, confidence, created_at, updated_at FROM facts WHERE session_id = ? ORDER BY updated_at DESC LIMIT ?",
                        (session_id, limit)
                    )

                rows = c.fetchall()
                facts = [
                    {
                        'id': r[0],
                        'session_id': r[1],
                        'fact_type': r[2],
                        'fact_key': r[3],
                        'fact_value': r[4],
                        'source_message_id': r[5],
                        'confidence': r[6],
                        'created_at': r[7],
                        'updated_at': r[8],
                    }
                    for r in rows
                ]

                logger.info("facts_retrieved", session_id=session_id, fact_type=fact_type, count=len(facts))
                return facts

        except Exception as e:
            logger.error("facts_retrieve_error", error=str(e), session_id=session_id)
            return []

    def format_facts_for_prompt(self, session_id: str) -> str:
        """Formatea los hechos de una sesión para incluirlos en el prompt del modelo."""
        facts = self.get_facts(session_id)
        if not facts:
            return ""

        # Agrupar por tipo
        grouped_facts = {}
        for fact in facts:
            fact_type = fact['fact_type']
            if fact_type not in grouped_facts:
                grouped_facts[fact_type] = []
            grouped_facts[fact_type].append(fact)

        # Mapeo de tipos a etiquetas en español
        type_labels = {
            'name': '👤 Personal',
            'age': '👤 Personal',
            'location': '👤 Personal',
            'employer': '💼 Profesional',
            'job_title': '💼 Profesional',
            'current_project': '💼 Profesional',
            'likes': '⭐ Preferencias',
            'dislikes': '⭐ Preferencias',
        }

        sections = []
        for fact_type, type_facts in grouped_facts.items():
            label = type_labels.get(fact_type, f'📋 {fact_type.title()}')
            fact_lines = []

            for fact in type_facts:
                # Formatear según el tipo
                if fact_type == 'name':
                    fact_lines.append(f"  • Se llama {fact['fact_value']}")
                elif fact_type == 'age':
                    fact_lines.append(f"  • Tiene {fact['fact_value']} años")
                elif fact_type == 'location':
                    fact_lines.append(f"  • Vive en {fact['fact_value']}")
                elif fact_type == 'employer':
                    fact_lines.append(f"  • Trabaja en {fact['fact_value']}")
                elif fact_type == 'job_title':
                    fact_lines.append(f"  • Su cargo es {fact['fact_value']}")
                elif fact_type == 'current_project':
                    fact_lines.append(f"  • Está trabajando en {fact['fact_value']}")
                elif fact_type == 'likes':
                    fact_lines.append(f"  • Le gusta {fact['fact_value']}")
                elif fact_type == 'dislikes':
                    fact_lines.append(f"  • No le gusta {fact['fact_value']}")
                else:
                    fact_lines.append(f"  • {fact['fact_value']}")

            if fact_lines:
                sections.append(f"{label}:\n" + "\n".join(fact_lines))

        if sections:
            formatted = "--- Información sobre el usuario ---\n" + "\n".join(sections) + "\n--- Fin información usuario ---"
            logger.info("facts_formatted", session_id=session_id, sections=len(sections))
            return formatted

        return ""

    def delete_fact(self, fact_id: int) -> bool:
        """Elimina un hecho por su ID."""
        try:
            with _get_conn() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
                deleted = c.rowcount > 0

                if deleted:
                    logger.info("fact_deleted", fact_id=fact_id)
                else:
                    logger.warning("fact_not_found", fact_id=fact_id)

                return deleted

        except Exception as e:
            logger.error("fact_delete_error", error=str(e), fact_id=fact_id)
            return False


# Instancia global
episodic_memory = EpisodicMemory()