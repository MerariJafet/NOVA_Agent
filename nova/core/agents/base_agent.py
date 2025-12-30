"""
Clase base abstracta para todos los agentes especialistas.
Define la interfaz común y comportamiento base.

Sprint 5 - Fase 3
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from utils.logging import get_logger

logger = get_logger("core.agents.base_agent")


class BaseAgent(ABC):
    """
    Clase base abstracta para agentes especialistas.

    Todos los agentes deben heredar de esta clase e implementar
    los métodos abstractos definidos aquí.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        specialty: str,
        description: str,
        priority: int = 5,
        model_preference: Optional[str] = None
    ):
        """
        Inicializa agente base.

        Args:
            agent_id: ID único del agente
            name: Nombre legible del agente
            specialty: Especialidad principal (ej: 'business', 'programming')
            description: Descripción de capacidades
            priority: Prioridad (1-10, mayor = más prioritario)
            model_preference: Modelo preferido (opcional)
        """
        self.agent_id = agent_id
        self.name = name
        self.specialty = specialty
        self.description = description
        self.priority = priority
        self.model_preference = model_preference or "auto"

        # Estado
        self.enabled = True
        self.created_at = datetime.now()

        # Estadísticas
        self.activation_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_response_time = 0.0

        logger.info(
            "agent_initialized",
            agent_id=agent_id,
            name=name,
            specialty=specialty
        )

    @abstractmethod
    def can_handle(self, query: str, context: Optional[Dict] = None) -> float:
        """
        Evalúa si este agente puede manejar la query.

        Args:
            query: Pregunta del usuario
            context: Contexto adicional

        Returns:
            Float entre 0.0 y 1.0 indicando confianza
        """
        pass

    @abstractmethod
    async def process_query(
        self,
        query: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Procesa la query y retorna respuesta estructurada.

        Args:
            query: Pregunta del usuario
            context: Contexto adicional
            **kwargs: Parámetros adicionales

        Returns:
            Dict con respuesta estructurada
        """
        pass

    def enable(self):
        """Habilita el agente."""
        self.enabled = True
        logger.info("agent_enabled", agent_id=self.agent_id)

    def disable(self):
        """Deshabilita el agente."""
        self.enabled = False
        logger.info("agent_disabled", agent_id=self.agent_id)

    def is_enabled(self) -> bool:
        """Retorna si el agente está habilitado."""
        return self.enabled

    def record_activation(self):
        """Registra una activación del agente."""
        self.activation_count += 1

    def record_success(self, response_time: float = 0.0):
        """Registra una respuesta exitosa."""
        self.success_count += 1
        self.total_response_time += response_time

    def record_failure(self):
        """Registra una respuesta fallida."""
        self.failure_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del agente."""
        total_responses = self.success_count + self.failure_count
        avg_response_time = (
            self.total_response_time / total_responses
            if total_responses > 0 else 0.0
        )

        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'specialty': self.specialty,
            'enabled': self.enabled,
            'priority': self.priority,
            'model_preference': self.model_preference,
            'activation_count': self.activation_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': (
                self.success_count / total_responses
                if total_responses > 0 else 0.0
            ),
            'avg_response_time': avg_response_time,
            'created_at': self.created_at.isoformat()
        }

    def reset_stats(self):
        """Reinicia estadísticas del agente."""
        self.activation_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_response_time = 0.0
        logger.info("agent_stats_reset", agent_id=self.agent_id)

    def get_capabilities(self) -> Dict[str, Any]:
        """Retorna capacidades del agente."""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'specialty': self.specialty,
            'description': self.description,
            'priority': self.priority,
            'model_preference': self.model_preference,
            'enabled': self.enabled
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.agent_id}, specialty={self.specialty}, enabled={self.enabled})>"