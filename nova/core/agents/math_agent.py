"""
Agente especialista en matemáticas y resolución de problemas matemáticos.
Maneja consultas sobre álgebra, cálculo, geometría, estadística, lógica.

Sprint 5 - Fase 3
"""

import re
from typing import Dict, Any, Optional, List

from .base_agent import BaseAgent
from utils.logging import get_logger

logger = get_logger("core.agents.math_agent")


class MathAgent(BaseAgent):
    """
    Agente especialista en matemáticas y resolución de problemas matemáticos.

    Capacidades:
    - Resolución de ecuaciones y sistemas
    - Cálculo diferencial e integral
    - Geometría y trigonometría
    - Estadística y probabilidad
    - Lógica matemática
    - Verificación de demostraciones
    """

    def __init__(self):
        super().__init__(
            agent_id="math_agent",
            name="Mathematics Expert",
            specialty="math",
            description="Especialista en matemáticas, ecuaciones y problemas matemáticos",
            priority=7,
            model_preference="mixtral:8x7b"
        )

        # Palabras clave para detección
        self.math_keywords = {
            'matemáticas', 'matematica', 'math', 'mathematics',
            'ecuación', 'equation', 'ecuaciones', 'equations',
            'álgebra', 'algebra', 'álgebra', 'algebra',
            'cálculo', 'calculo', 'calculus', 'integral', 'derivative', 'derivada',
            'geometría', 'geometria', 'geometry', 'triángulo', 'triangle', 'círculo', 'circle',
            'estadística', 'estadistica', 'statistics', 'probabilidad', 'probability',
            'lógica', 'logica', 'logic', 'demostración', 'demostracion', 'proof',
            'número', 'numero', 'number', 'primo', 'prime', 'factorial', 'fibonacci',
            'matriz', 'matrix', 'vector', 'vector', 'coordenadas', 'coordinates',
            'función', 'funcion', 'function', 'línea', 'linea', 'line', 'punto', 'point',
            'teorema', 'theorem', 'axioma', 'axiom', 'postulado', 'postulate',
            'resolver', 'solve', 'calcular', 'calculate', 'simplificar', 'simplify'
        }

        # Patrones de expresiones matemáticas
        self.math_patterns = [
            r'\d+[\+\-\*\/\^\=]\d+',  # Operaciones básicas
            r'x[\+\-\*\/\^\=]\d+',    # Variables con números
            r'\d+x[\+\-\*\/\^\=]',    # Números con variables
            r'x\^?\d+',               # Potencias
            r'sin\(|cos\(|tan\(|log\(|ln\(',  # Funciones trigonométricas/logarítmicas
            r'∫|∂|∑|∏|√|π|∞',        # Símbolos matemáticos
            r'\d+\s*[\+\-\*\/]\s*\d+', # Operaciones con espacios
            r'[\(\[\{].*[\)\]\}]',     # Paréntesis, corchetes, llaves
        ]

        # Patrones de frases para alta confianza
        self.high_confidence_patterns = [
            r'(resolver|resuelve|calcula|calcule) (la|el|esta|este)',
            r'(ecuación|equation) (de|del|de la)',
            r'(problema|problem) (matemático|matematico|de matemáticas)',
            r'(demostrar|demuestra|prueba|proof) (que|el|la)',
            r'(integral|derivada|derivative) (de|del)',
            r'(área|area|perímetro|perimetro|volumen) (de|del)',
            r'(probabilidad|probability) (de|del|que)',
            r'(estadística|statistics) (de|sobre|para)'
        ]

    def can_handle(self, query: str, context: Optional[Dict] = None) -> float:
        """
        Evalúa si puede manejar consultas matemáticas.

        Lógica de confianza:
        - Alta (0.8-1.0): Expresiones matemáticas + patrones específicos
        - Media-Alta (0.6-0.8): Patrones específicos de matemáticas
        - Media (0.4-0.6): Expresiones matemáticas o términos técnicos
        - Baja (0.2-0.4): Algunos términos matemáticos
        - Muy baja (0.0-0.1): Pocas o ninguna palabra clave
        """
        query_lower = query.lower()

        # Verificar expresiones matemáticas (alta confianza automática)
        has_math_expressions = any(re.search(pattern, query) for pattern in self.math_patterns)

        # Verificar patrones de alta confianza
        for pattern in self.high_confidence_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                confidence = 0.9 if has_math_expressions else 0.8
                logger.info("math_high_confidence_pattern",
                           agent_id=self.agent_id,
                           pattern=pattern,
                           has_expressions=has_math_expressions)
                return confidence

        # Contar palabras clave
        keyword_count = sum(1 for keyword in self.math_keywords
                          if keyword in query_lower)

        # Verificar símbolos matemáticos específicos
        math_symbols = ['=', '+', '-', '*', '/', '^', '√', '∫', '∂', '∑', '∏', 'π', '∞']
        symbol_count = sum(1 for symbol in math_symbols if symbol in query)

        # Calcular confianza
        total_words = len(query.split())
        if total_words == 0:
            return 0.0

        density = keyword_count / total_words
        symbol_bonus = min(0.3, symbol_count * 0.1)

        if has_math_expressions:
            confidence = min(1.0, 0.7 + density + symbol_bonus)
        elif density >= 0.1:  # Alta densidad matemática
            confidence = min(0.8, 0.5 + density + symbol_bonus)
        elif density >= 0.05:  # Media densidad matemática
            confidence = min(0.6, 0.3 + density + symbol_bonus)
        elif keyword_count >= 3:  # Múltiples términos matemáticos
            confidence = 0.4 + symbol_bonus
        elif keyword_count >= 1:  # Al menos un término matemático
            confidence = 0.2 + symbol_bonus
        else:
            confidence = 0.0

        logger.info("math_confidence_calculated",
                   agent_id=self.agent_id,
                   keyword_count=keyword_count,
                   symbol_count=symbol_count,
                   density=density,
                   has_expressions=has_math_expressions,
                   confidence=confidence)

        return confidence

    async def process_query(
        self,
        query: str,
        context: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Procesa consultas matemáticas y retorna análisis estructurado.
        """
        import time
        start_time = time.time()

        try:
            self.record_activation()

            # Análisis de la consulta
            analysis = self._analyze_math_query(query)

            # Generar respuesta estructurada
            response = {
                'agent_id': self.agent_id,
                'agent_name': self.name,
                'specialty': self.specialty,
                'confidence': self.can_handle(query, context),
                'query_analysis': analysis,
                'math_expressions': self._extract_math_expressions(query),
                'solution_steps': self._generate_solution_steps(analysis),
                'explanation': self._provide_explanation(analysis),
                'related_concepts': self._suggest_related_concepts(analysis),
                'practice_problems': self._suggest_practice_problems(analysis)
            }

            response_time = time.time() - start_time
            self.record_success(response_time)

            logger.info("math_query_processed",
                       agent_id=self.agent_id,
                       response_time=response_time)

            return response

        except Exception as e:
            response_time = time.time() - start_time
            self.record_failure()

            logger.error("math_query_failed",
                        agent_id=self.agent_id,
                        error=str(e),
                        response_time=response_time)

            return {
                'agent_id': self.agent_id,
                'error': f'Error procesando consulta matemática: {str(e)}',
                'confidence': 0.0
            }

    def _analyze_math_query(self, query: str) -> Dict[str, Any]:
        """Analiza la consulta matemática."""
        analysis = {
            'math_area': 'unknown',
            'difficulty': 'medium',
            'has_equations': False,
            'has_calculus': False,
            'has_geometry': False,
            'has_statistics': False,
            'variables': [],
            'numbers': []
        }

        query_lower = query.lower()

        # Detectar área matemática
        if any(word in query_lower for word in ['derivada', 'integral', 'límit', 'limite', 'diferencial']):
            analysis['math_area'] = 'calculus'
            analysis['has_calculus'] = True
        elif any(word in query_lower for word in ['triángulo', 'círculo', 'cuadrado', 'rectángulo', 'área', 'perímetro', 'volumen']):
            analysis['math_area'] = 'geometry'
            analysis['has_geometry'] = True
        elif any(word in query_lower for word in ['probabilidad', 'estadística', 'media', 'mediana', 'desviación']):
            analysis['math_area'] = 'statistics'
            analysis['has_statistics'] = True
        elif any(word in query_lower for word in ['ecuación', 'sistema', 'incógnita', 'resolver']):
            analysis['math_area'] = 'algebra'
            analysis['has_equations'] = True
        elif any(word in query_lower for word in ['demostración', 'teorema', 'axioma', 'postulado']):
            analysis['math_area'] = 'logic'
        elif '=' in query or any(word in query_lower for word in ['igual', 'equality']):
            analysis['math_area'] = 'equations'

        # Extraer variables (letras individuales)
        variables = set(re.findall(r'\b[a-zA-Z]\b', query))
        analysis['variables'] = sorted(list(variables - {'a', 'e', 'i', 'o', 'u', 'y'}))  # Excluir vocales comunes

        # Extraer números
        numbers = re.findall(r'\d+\.?\d*', query)
        analysis['numbers'] = [float(n) for n in numbers]

        # Determinar dificultad
        complexity_indicators = [
            analysis['has_calculus'],
            len(analysis['variables']) > 2,
            len(analysis['numbers']) > 5,
            'sistema' in query_lower,
            'matriz' in query_lower,
            'integral' in query_lower
        ]

        if sum(complexity_indicators) >= 3:
            analysis['difficulty'] = 'high'
        elif sum(complexity_indicators) >= 1:
            analysis['difficulty'] = 'medium'
        else:
            analysis['difficulty'] = 'low'

        return analysis

    def _extract_math_expressions(self, query: str) -> List[str]:
        """Extrae expresiones matemáticas de la consulta."""
        expressions = []

        # Buscar expresiones entre símbolos matemáticos
        math_segments = re.findall(r'[^\w\s]*[\w\d\+\-\*\/\^\(\)\[\]\{\}\=]+[^\w\s]*', query)

        for segment in math_segments:
            # Limpiar y validar
            clean_segment = segment.strip()
            if len(clean_segment) > 2 and any(char in clean_segment for char in '+=*/^-()[]{}'):
                expressions.append(clean_segment)

        # Buscar ecuaciones completas
        equations = re.findall(r'[^.!?]*=.*?(?=[.!?]|$)', query)
        for eq in equations:
            eq_clean = eq.strip()
            if len(eq_clean) > 3:
                expressions.append(eq_clean)

        return list(set(expressions))  # Eliminar duplicados

    def _generate_solution_steps(self, analysis: Dict[str, Any]) -> List[str]:
        """Genera pasos para resolver el problema."""
        steps = []

        math_area = analysis.get('math_area', 'unknown')
        difficulty = analysis.get('difficulty', 'medium')

        # Pasos por área matemática
        if math_area == 'algebra':
            steps = [
                '1. Identifica las variables e incógnitas en la ecuación',
                '2. Agrupa términos semejantes (constantes y variables)',
                '3. Aísla la variable en un lado de la ecuación',
                '4. Realiza operaciones inversas para despejar la variable',
                '5. Verifica la solución sustituyendo en la ecuación original'
            ]
        elif math_area == 'calculus':
            if 'derivada' in str(analysis):
                steps = [
                    '1. Identifica la función a derivar',
                    '2. Aplica reglas de derivación apropiadas',
                    '3. Simplifica la expresión resultante',
                    '4. Verifica el dominio de la función derivada'
                ]
            elif 'integral' in str(analysis):
                steps = [
                    '1. Identifica los límites de integración',
                    '2. Encuentra la antiderivada de la función',
                    '3. Evalúa la antiderivada en los límites',
                    '4. Resta el resultado inferior del superior'
                ]
        elif math_area == 'geometry':
            steps = [
                '1. Identifica la figura geométrica y sus propiedades',
                '2. Recuerda las fórmulas relevantes (área, perímetro, volumen)',
                '3. Sustituye los valores conocidos en la fórmula',
                '4. Realiza los cálculos necesarios'
            ]
        elif math_area == 'statistics':
            steps = [
                '1. Organiza los datos disponibles',
                '2. Identifica qué medida estadística necesitas',
                '3. Aplica la fórmula correspondiente',
                '4. Interpreta el resultado en contexto'
            ]

        # Ajustar por dificultad
        if difficulty == 'high':
            steps.insert(0, '0. COMPLEJO: Divide el problema en partes más pequeñas')
        elif difficulty == 'low':
            steps.append('Bonus: Intenta resolver mentalmente primero')

        # Pasos generales si no hay específicos
        if not steps:
            steps = [
                '1. Lee el problema completo y entiende qué se pide',
                '2. Identifica la información dada y la información necesaria',
                '3. Elige el método o fórmula apropiada',
                '4. Ejecuta los cálculos paso a paso',
                '5. Verifica que la respuesta tenga sentido lógico'
            ]

        return steps

    def _provide_explanation(self, analysis: Dict[str, Any]) -> str:
        """Proporciona explicación conceptual."""
        math_area = analysis.get('math_area', 'unknown')

        explanations = {
            'algebra': 'El álgebra es el estudio de las estructuras matemáticas y sus operaciones. '
                      'Las ecuaciones son igualdades que relacionan expresiones algebraicas. '
                      'Resolver ecuaciones significa encontrar los valores que hacen la igualdad verdadera.',

            'calculus': 'El cálculo es el estudio del cambio y la acumulación. '
                       'Las derivadas miden tasas de cambio instantáneo, mientras que las integrales '
                       'miden acumulación total. Son herramientas fundamentales en ciencia e ingeniería.',

            'geometry': 'La geometría estudia las propiedades del espacio, formas y figuras. '
                       'Incluye el cálculo de áreas, perímetros, volúmenes y relaciones entre figuras. '
                       'Es esencial en diseño, arquitectura y física.',

            'statistics': 'La estadística estudia la recolección, análisis e interpretación de datos. '
                         'Ayuda a tomar decisiones informadas bajo incertidumbre y a entender patrones '
                         'en conjuntos de datos.',

            'logic': 'La lógica matemática formaliza el razonamiento correcto. '
                    'Las demostraciones verifican que una afirmación es necesariamente verdadera '
                    'basándose en axiomas y reglas de inferencia.'
        }

        return explanations.get(math_area, 'Esta consulta involucra conceptos matemáticos. '
                                          'Las matemáticas son el lenguaje de las ciencias y la base '
                                          'de la resolución sistemática de problemas.')

    def _suggest_related_concepts(self, analysis: Dict[str, Any]) -> List[str]:
        """Sugiere conceptos relacionados."""
        concepts = []

        math_area = analysis.get('math_area', 'unknown')

        if math_area == 'algebra':
            concepts = [
                'Ecuaciones lineales y cuadráticas',
                'Sistemas de ecuaciones',
                'Funciones y gráficas',
                'Inecuaciones',
                'Números complejos'
            ]
        elif math_area == 'calculus':
            concepts = [
                'Límites y continuidad',
                'Reglas de derivación',
                'Técnicas de integración',
                'Series infinitas',
                'Ecuaciones diferenciales'
            ]
        elif math_area == 'geometry':
            concepts = [
                'Teorema de Pitágoras',
                'Semejanza de triángulos',
                'Coordenadas cartesianas',
                'Geometría analítica',
                'Geometría del espacio'
            ]
        elif math_area == 'statistics':
            concepts = [
                'Distribuciones de probabilidad',
                'Teorema del límite central',
                'Intervalos de confianza',
                'Pruebas de hipótesis',
                'Regresión lineal'
            ]

        return concepts

    def _suggest_practice_problems(self, analysis: Dict[str, Any]) -> List[str]:
        """Sugiere problemas para practicar."""
        problems = []

        math_area = analysis.get('math_area', 'unknown')
        difficulty = analysis.get('difficulty', 'medium')

        if math_area == 'algebra':
            if difficulty == 'low':
                problems = [
                    'Resolver: 2x + 3 = 7',
                    'Factorizar: x² + 5x + 6 = 0',
                    'Simplificar: (x+2)(x-3)'
                ]
            else:
                problems = [
                    'Resolver el sistema: 2x + y = 5, x - y = 1',
                    'Encontrar el dominio de f(x) = √(x-2)',
                    'Demostrar que (a+b)² = a² + 2ab + b²'
                ]
        elif math_area == 'calculus':
            problems = [
                'Derivar: f(x) = x³ + 2x² - x + 1',
                'Integrar: ∫(x² + 3x + 1)dx',
                'Encontrar el límite: lim(x→0) sin(x)/x'
            ]
        elif math_area == 'geometry':
            problems = [
                'Calcular el área de un círculo de radio 5',
                'Encontrar la hipotenusa de un triángulo rectángulo con catetos 3 y 4',
                'Calcular el volumen de una esfera de radio 3'
            ]

        # Problemas generales si no hay específicos
        if not problems:
            problems = [
                'Practica operaciones básicas con fracciones',
                'Resuelve ecuaciones lineales simples',
                'Calcula áreas y perímetros de figuras básicas',
                'Trabaja con porcentajes y proporciones'
            ]

        return problems