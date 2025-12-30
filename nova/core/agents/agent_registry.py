"""
Sistema de registro y gestión de agentes especialistas.
Mantiene catálogo de agentes, activación/desactivación y routing.

Sprint 5 - Fase 3
"""

from typing import Dict, List, Optional, Any
from collections import defaultdict
import json

from .base_agent import BaseAgent
from utils.logging import get_logger

logger = get_logger("core.agents.agent_registry")


class AgentRegistry:
    """
    Registro centralizado de agentes especialistas.
    
    Responsabilidades:
    - Mantener catálogo de agentes activos
    - Activar/desactivar agentes dinámicamente
    - Routing a agentes apropiados según query
    - Gestión de estadísticas agregadas
    """
    
    def __init__(self):
        """Inicializa registro vacío."""
        self._agents: Dict[str, BaseAgent] = {}
        self._agents_by_specialty: Dict[str, List[BaseAgent]] = defaultdict(list)
        logger.info("agent_registry_initialized")
    
    def register(self, agent: BaseAgent) -> bool:
        """
        Registra un agente en el sistema.
        
        Args:
            agent: Instancia de BaseAgent o subclase
            
        Returns:
            True si registrado exitosamente
        """
        if not isinstance(agent, BaseAgent):
            logger.error(
                "invalid_agent_type",
                agent_type=type(agent).__name__
            )
            return False
        
        if agent.agent_id in self._agents:
            logger.warning(
                "agent_already_registered",
                agent_id=agent.agent_id
            )
            return False
        
        # Registrar agente
        self._agents[agent.agent_id] = agent
        self._agents_by_specialty[agent.specialty].append(agent)
        
        logger.info(
            "agent_registered",
            agent_id=agent.agent_id,
            name=agent.name,
            specialty=agent.specialty
        )
        
        return True
    
    def unregister(self, agent_id: str) -> bool:
        """
        Elimina un agente del registro.
        
        Args:
            agent_id: ID del agente
            
        Returns:
            True si eliminado exitosamente
        """
        if agent_id not in self._agents:
            logger.warning("agent_not_found", agent_id=agent_id)
            return False
        
        agent = self._agents[agent_id]
        specialty = agent.specialty
        
        # Eliminar de registro principal
        del self._agents[agent_id]
        
        # Eliminar de especialidad
        self._agents_by_specialty[specialty] = [
            a for a in self._agents_by_specialty[specialty]
            if a.agent_id != agent_id
        ]
        
        logger.info("agent_unregistered", agent_id=agent_id)
        return True
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Obtiene agente por ID."""
        return self._agents.get(agent_id)
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Retorna lista de todos los agentes registrados."""
        return list(self._agents.values())
    
    def get_enabled_agents(self) -> List[BaseAgent]:
        """Retorna solo agentes habilitados."""
        return [a for a in self._agents.values() if a.enabled]
    
    def get_agents_by_specialty(self, specialty: str) -> List[BaseAgent]:
        """Retorna agentes de una especialidad específica."""
        return self._agents_by_specialty.get(specialty, [])
    
    def enable_agent(self, agent_id: str) -> bool:
        """Habilita un agente."""
        agent = self.get_agent(agent_id)
        if agent:
            agent.enable()
            return True
        return False
    
    def disable_agent(self, agent_id: str) -> bool:
        """Deshabilita un agente."""
        agent = self.get_agent(agent_id)
        if agent:
            agent.disable()
            return True
        return False
    
    def find_capable_agents(
        self,
        query: str,
        context: Optional[Dict] = None,
        min_confidence: float = 0.3,
        max_agents: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Encuentra agentes capaces de manejar la query.
        
        Args:
            query: Pregunta del usuario
            context: Contexto adicional
            min_confidence: Confianza mínima requerida
            max_agents: Máximo de agentes a retornar
            
        Returns:
            Lista de dicts con agent y confidence score, ordenados por score
        """
        capable_agents = []
        
        for agent in self.get_enabled_agents():
            try:
                confidence = agent.can_handle(query, context)
                
                if confidence >= min_confidence:
                    capable_agents.append({
                        'agent': agent,
                        'agent_id': agent.agent_id,
                        'name': agent.name,
                        'specialty': agent.specialty,
                        'confidence': confidence,
                        'priority': agent.priority
                    })
            
            except Exception as e:
                logger.error(
                    "agent_evaluation_failed",
                    agent_id=agent.agent_id,
                    error=str(e)
                )
        
        # Ordenar por: confidence (desc) → priority (desc)
        capable_agents.sort(
            key=lambda x: (x['confidence'], x['priority']),
            reverse=True
        )
        
        result = capable_agents[:max_agents]
        
        logger.info(
            "capable_agents_found",
            query_length=len(query),
            total_found=len(capable_agents),
            returned=len(result)
        )
        
        return result
    
    def get_best_agent(
        self,
        query: str,
        context: Optional[Dict] = None,
        min_confidence: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """
        Retorna el mejor agente para la query.
        
        Args:
            query: Pregunta del usuario
            context: Contexto adicional
            min_confidence: Confianza mínima
            
        Returns:
            Dict con agent y confidence, o None si no hay agente capaz
        """
        capable = self.find_capable_agents(
            query,
            context,
            min_confidence,
            max_agents=1
        )
        
        return capable[0] if capable else None
    
    def get_registry_stats(self) -> Dict:
        """Retorna estadísticas agregadas del registro."""
        all_agents = self.get_all_agents()
        enabled = self.get_enabled_agents()
        
        total_activations = sum(a.activation_count for a in all_agents)
        total_successes = sum(a.success_count for a in all_agents)
        
        # Agrupar por especialidad
        specialties = {}
        for specialty, agents in self._agents_by_specialty.items():
            specialties[specialty] = {
                'count': len(agents),
                'enabled': len([a for a in agents if a.enabled])
            }
        
        return {
            'total_agents': len(all_agents),
            'enabled_agents': len(enabled),
            'disabled_agents': len(all_agents) - len(enabled),
            'total_activations': total_activations,
            'total_successes': total_successes,
            'overall_success_rate': (
                total_successes / total_activations if total_activations > 0 else 0
            ),
            'specialties': specialties
        }
    
    def get_all_stats(self) -> List[Dict]:
        """Retorna estadísticas de todos los agentes."""
        return [agent.get_stats() for agent in self.get_all_agents()]
    
    def reset_all_stats(self):
        """Reinicia estadísticas de todos los agentes."""
        for agent in self.get_all_agents():
            agent.reset_stats()
        logger.info("all_stats_reset")
    
    def export_config(self) -> Dict:
        """Exporta configuración del registro."""
        return {
            'agents': [
                {
                    'agent_id': a.agent_id,
                    'name': a.name,
                    'specialty': a.specialty,
                    'enabled': a.enabled,
                    'priority': a.priority,
                    'model_preference': a.model_preference
                }
                for a in self.get_all_agents()
            ]
        }
    
    def __len__(self) -> int:
        """Retorna cantidad de agentes registrados."""
        return len(self._agents)
    
    def __repr__(self) -> str:
        return f"<AgentRegistry(agents={len(self._agents)}, enabled={len(self.get_enabled_agents())})>"


# Instancia global (singleton)
_agent_registry_instance = None

def get_agent_registry() -> AgentRegistry:
    """Retorna instancia singleton de AgentRegistry."""
    global _agent_registry_instance
    
    if _agent_registry_instance is None:
        _agent_registry_instance = AgentRegistry()
        logger.info("agent_registry_instance_created")
    
    return _agent_registry_instance