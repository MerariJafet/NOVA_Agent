"""
Agente especialista en análisis de negocio y estrategia empresarial.
Maneja consultas sobre emprendimiento, finanzas, marketing, operaciones.

Sprint 5 - Fase 3
"""

import re
from typing import Dict, Any, Optional, List

from .base_agent import BaseAgent
from utils.logging import get_logger

logger = get_logger("core.agents.business_agent")


class BusinessAgent(BaseAgent):
    """
    Agente especialista en análisis de negocio y estrategia empresarial.

    Capacidades:
    - Análisis de modelos de negocio
    - Estrategias de marketing y ventas
    - Análisis financiero básico
    - Planificación empresarial
    - Consultoría de emprendimiento
    """

    def __init__(self):
        super().__init__(
            agent_id="business_agent",
            name="Business Analyst",
            specialty="business",
            description="Especialista en análisis de negocio, estrategia empresarial y consultoría",
            priority=8,
            model_preference="dolphin-mistral:7b"
        )

        # Palabras clave para detección
        self.business_keywords = {
            'negocio', 'empresa', 'emprendimiento', 'startup', 'compañía',
            'marketing', 'ventas', 'cliente', 'mercado', 'competencia',
            'estrategia', 'plan', 'finanzas', 'inversión', 'ganancias',
            'pérdidas', 'ROI', 'beneficio', 'costos', 'presupuesto',
            'producto', 'servicio', 'precio', 'valor', 'brand', 'marca'
        }

        # Patrones de frases para alta confianza
        self.high_confidence_patterns = [
            r'cómo (empezar|montar|crear) (un|una) (negocio|empresa|startup)',
            r'estrategia (de|para) (marketing|ventas|negocio)',
            r'análisis (de|financiero|mercado|competencia)',
            r'plan (de|para) (negocio|empresa|marketing)',
            r'modelo de negocio',
            r'estudio de mercado',
            r'asesoramiento empresarial'
        ]

    def can_handle(self, query: str, context: Optional[Dict] = None) -> float:
        """
        Evalúa si puede manejar consultas de negocio.

        Lógica de confianza:
        - Alta (0.8-1.0): Patrones específicos de negocio
        - Media (0.5-0.7): Múltiples palabras clave de negocio
        - Baja (0.2-0.4): Algunas palabras clave de negocio
        - Muy baja (0.0-0.1): Pocas o ninguna palabra clave
        """
        query_lower = query.lower()

        # Verificar patrones de alta confianza
        for pattern in self.high_confidence_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.info("business_high_confidence_pattern",
                           agent_id=self.agent_id,
                           pattern=pattern)
                return 0.9

        # Contar palabras clave
        keyword_count = sum(1 for keyword in self.business_keywords
                          if keyword in query_lower)

        # Calcular confianza basada en densidad de palabras clave
        total_words = len(query.split())
        if total_words == 0:
            return 0.0

        density = keyword_count / total_words

        if density >= 0.15:  # Alta densidad
            confidence = min(0.8, 0.5 + density)
        elif density >= 0.08:  # Media densidad
            confidence = min(0.6, 0.3 + density)
        elif keyword_count >= 2:  # Al menos 2 palabras clave
            confidence = 0.4
        elif keyword_count == 1:  # Una palabra clave
            confidence = 0.2
        else:
            confidence = 0.0

        logger.info("business_confidence_calculated",
                   agent_id=self.agent_id,
                   keyword_count=keyword_count,
                   density=density,
                   confidence=confidence)

        return confidence

    async def process_query(
        self,
        query: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Procesa consultas de negocio y retorna análisis estructurado.
        """
        import time
        start_time = time.time()

        try:
            self.record_activation()

            # Análisis básico de la consulta
            analysis = self._analyze_business_query(query)

            # Generar respuesta estructurada
            response = {
                'agent_id': self.agent_id,
                'agent_name': self.name,
                'specialty': self.specialty,
                'confidence': self.can_handle(query, context),
                'query_analysis': analysis,
                'recommendations': self._generate_recommendations(analysis),
                'next_steps': self._suggest_next_steps(analysis),
                'disclaimer': 'Esta es una respuesta general. Para asesoramiento específico, consulta con un profesional calificado.'
            }

            response_time = time.time() - start_time
            self.record_success(response_time)

            logger.info("business_query_processed",
                       agent_id=self.agent_id,
                       response_time=response_time)

            return response

        except Exception as e:
            response_time = time.time() - start_time
            self.record_failure()

            logger.error("business_query_failed",
                        agent_id=self.agent_id,
                        error=str(e),
                        response_time=response_time)

            return {
                'agent_id': self.agent_id,
                'error': f'Error procesando consulta de negocio: {str(e)}',
                'confidence': 0.0
            }

    def _analyze_business_query(self, query: str) -> Dict[str, Any]:
        """Analiza la consulta y extrae elementos clave."""
        analysis = {
            'query_type': 'unknown',
            'business_areas': [],
            'urgency_level': 'medium',
            'complexity': 'medium'
        }

        query_lower = query.lower()

        # Determinar tipo de consulta
        if any(word in query_lower for word in ['empezar', 'montar', 'crear', 'startup']):
            analysis['query_type'] = 'startup_creation'
        elif any(word in query_lower for word in ['marketing', 'ventas', 'cliente']):
            analysis['query_type'] = 'marketing_sales'
        elif any(word in query_lower for word in ['finanzas', 'dinero', 'ganancias', 'costos']):
            analysis['query_type'] = 'financial'
        elif any(word in query_lower for word in ['estrategia', 'plan', 'competencia']):
            analysis['query_type'] = 'strategy_planning'

        # Identificar áreas de negocio
        areas_keywords = {
            'marketing': ['marketing', 'marca', 'cliente', 'publicidad'],
            'sales': ['ventas', 'cliente', 'precio', 'contrato'],
            'finance': ['finanzas', 'dinero', 'ganancias', 'costos', 'presupuesto'],
            'operations': ['operaciones', 'proceso', 'eficiencia', 'producción'],
            'strategy': ['estrategia', 'plan', 'competencia', 'mercado']
        }

        for area, keywords in areas_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                analysis['business_areas'].append(area)

        # Determinar urgencia
        if any(word in query_lower for word in ['urgente', 'inmediato', 'rápido', 'ya']):
            analysis['urgency_level'] = 'high'
        elif any(word in query_lower for word in ['tiempo', 'pronto', 'meses']):
            analysis['urgency_level'] = 'medium'
        else:
            analysis['urgency_level'] = 'low'

        # Determinar complejidad
        word_count = len(query.split())
        if word_count > 50:
            analysis['complexity'] = 'high'
        elif word_count > 20:
            analysis['complexity'] = 'medium'
        else:
            analysis['complexity'] = 'low'

        return analysis

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones basadas en el análisis."""
        recommendations = []

        query_type = analysis.get('query_type', 'unknown')
        areas = analysis.get('business_areas', [])
        urgency = analysis.get('urgency_level', 'medium')

        # Recomendaciones por tipo de consulta
        if query_type == 'startup_creation':
            recommendations.extend([
                'Define claramente tu propuesta de valor y problema que resuelves',
                'Realiza un análisis de mercado básico antes de invertir tiempo/money',
                'Considera comenzar con un MVP (Producto Mínimo Viable)',
                'Busca mentores o comunidades de emprendedores'
            ])
        elif query_type == 'marketing_sales':
            recommendations.extend([
                'Identifica tu cliente ideal (buyer persona)',
                'Define tu estrategia de precios y posicionamiento',
                'Utiliza canales digitales para llegar a tu audiencia',
                'Mide y analiza los resultados de tus campañas'
            ])
        elif query_type == 'financial':
            recommendations.extend([
                'Mantén registros financieros claros y actualizados',
                'Calcula tu punto de equilibrio y márgenes de ganancia',
                'Considera diferentes fuentes de financiamiento',
                'Consulta con un contador o asesor financiero'
            ])
        elif query_type == 'strategy_planning':
            recommendations.extend([
                'Realiza un análisis SWOT (Fortalezas, Oportunidades, Debilidades, Amenazas)',
                'Define objetivos SMART (Específicos, Medibles, Alcanzables, Relevantes, Temporales)',
                'Monitorea a tu competencia regularmente',
                'Adapta tu estrategia basado en feedback del mercado'
            ])

        # Recomendaciones por urgencia
        if urgency == 'high':
            recommendations.insert(0, '🚨 PRIORIDAD: Esta consulta requiere atención inmediata')
        elif urgency == 'low':
            recommendations.append('📅 Esta es una decisión estratégica que puede tomarse con tiempo')

        # Recomendaciones generales si no hay específicas
        if not recommendations:
            recommendations = [
                'Define claramente tus objetivos de negocio',
                'Investiga el mercado y competencia',
                'Considera el impacto financiero de tus decisiones',
                'Busca asesoramiento profesional cuando sea necesario'
            ]

        return recommendations

    def _suggest_next_steps(self, analysis: Dict[str, Any]) -> List[str]:
        """Sugiere próximos pasos basados en el análisis."""
        next_steps = []

        query_type = analysis.get('query_type', 'unknown')
        complexity = analysis.get('complexity', 'medium')

        # Pasos por tipo de consulta
        if query_type == 'startup_creation':
            next_steps = [
                '1. Valida tu idea con potenciales clientes (mínimo 10 entrevistas)',
                '2. Crea un plan de negocio básico con proyecciones financieras',
                '3. Desarrolla un prototipo o landing page',
                '4. Busca feedback de mentores o inversores'
            ]
        elif query_type in ['marketing_sales', 'strategy_planning']:
            next_steps = [
                '1. Define métricas de éxito claras',
                '2. Implementa cambios de forma gradual',
                '3. Mide resultados y ajusta según feedback',
                '4. Documenta lecciones aprendidas'
            ]
        elif query_type == 'financial':
            next_steps = [
                '1. Reúne toda la información financiera necesaria',
                '2. Consulta con un profesional calificado',
                '3. Crea un presupuesto realista',
                '4. Monitorea gastos e ingresos regularmente'
            ]

        # Ajustar por complejidad
        if complexity == 'high':
            next_steps.insert(0, '0. Divide el problema en partes más pequeñas y manejables')
        elif complexity == 'low':
            next_steps.append('Bonus: Considera automatizar procesos repetitivos')

        return next_steps