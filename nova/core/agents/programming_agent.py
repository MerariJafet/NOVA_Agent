"""
Agente especialista en programación y desarrollo de software.
Maneja consultas sobre código, algoritmos, debugging, arquitectura.

Sprint 5 - Fase 3
"""

import re
from typing import Dict, Any, Optional, List

from .base_agent import BaseAgent
from utils.logging import get_logger

logger = get_logger("core.agents.programming_agent")


class ProgrammingAgent(BaseAgent):
    """
    Agente especialista en programación y desarrollo de software.

    Capacidades:
    - Análisis y corrección de código
    - Diseño de algoritmos
    - Debugging y resolución de errores
    - Arquitectura de software
    - Mejores prácticas de desarrollo
    """

    def __init__(self):
        super().__init__(
            agent_id="programming_agent",
            name="Programming Expert",
            specialty="programming",
            description="Especialista en desarrollo de software, algoritmos y debugging",
            priority=9,
            model_preference="dolphin-mistral:7b",
        )

        # Palabras clave para detección
        self.programming_keywords = {
            "código",
            "programar",
            "programación",
            "code",
            "coding",
            "programming",
            "función",
            "clase",
            "objeto",
            "variable",
            "algoritmo",
            "algorithm",
            "debug",
            "error",
            "bug",
            "exception",
            "debugging",
            "fix",
            "python",
            "javascript",
            "java",
            "c++",
            "php",
            "ruby",
            "go",
            "rust",
            "html",
            "css",
            "sql",
            "database",
            "api",
            "framework",
            "library",
            "git",
            "github",
            "version",
            "control",
            "merge",
            "commit",
            "branch",
            "test",
            "testing",
            "unit",
            "integration",
            "tdd",
            "ci",
            "cd",
            "performance",
            "optimization",
            "memory",
            "cpu",
            "efficiency",
        }

        # Patrones de frases para alta confianza
        self.high_confidence_patterns = [
            r"(cómo|como) (programar|hacer|implementar|crear) (un|una)",
            r"(error|bug|problema) (en|con) (el|mi) (código|código)",
            r"(ayuda|help) (con|para) (programar|programación|coding)",
            r"(revisar|analizar|corregir) (mi|el) código",
            r"debug(g(ea)?r?|ear) (un|mi) (programa|código|aplicación)",
            r"(optimiz|optim)ar (el|mi) código",
            r"(mejor|best) (práctica|practice) (de|en) (programación|coding)",
            r"(algoritmo|algorithm) (para|de|que)",
            r"(estructura|design|arquitectura) (de|del) (software|código)",
        ]

    def can_handle(self, query: str, context: Optional[Dict] = None) -> float:
        """
        Evalúa si puede manejar consultas de programación.

        Lógica de confianza:
        - Alta (0.8-1.0): Patrones específicos de programación + código
        - Media-Alta (0.6-0.8): Patrones específicos de programación
        - Media (0.4-0.6): Lenguajes de programación + términos técnicos
        - Baja (0.2-0.4): Algunos términos técnicos de programación
        - Muy baja (0.0-0.1): Pocas o ninguna palabra clave
        """
        query_lower = query.lower()

        # Verificar si contiene código (alta confianza automática)
        code_indicators = [
            "```",
            "def ",
            "class ",
            "function",
            "import ",
            "from ",
            "print(",
        ]
        has_code = any(indicator in query for indicator in code_indicators)

        # Verificar patrones de alta confianza
        for pattern in self.high_confidence_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                confidence = 0.9 if has_code else 0.8
                logger.info(
                    "programming_high_confidence_pattern",
                    agent_id=self.agent_id,
                    pattern=pattern,
                    has_code=has_code,
                )
                return confidence

        # Contar palabras clave
        keyword_count = sum(
            1 for keyword in self.programming_keywords if keyword in query_lower
        )

        # Verificar lenguajes de programación específicos
        languages = [
            "python",
            "javascript",
            "java",
            "c\\+\\+",
            "php",
            "ruby",
            "go",
            "rust",
            "typescript",
        ]
        language_count = sum(
            1 for lang in languages if re.search(r"\b" + lang + r"\b", query_lower)
        )

        # Calcular confianza
        total_words = len(query.split())
        if total_words == 0:
            return 0.0

        density = keyword_count / total_words
        language_bonus = min(0.2, language_count * 0.1)

        if has_code:
            confidence = min(1.0, 0.7 + density + language_bonus)
        elif density >= 0.12:  # Alta densidad técnica
            confidence = min(0.8, 0.5 + density + language_bonus)
        elif density >= 0.06:  # Media densidad técnica
            confidence = min(0.6, 0.3 + density + language_bonus)
        elif keyword_count >= 3:  # Múltiples términos técnicos
            confidence = 0.4 + language_bonus
        elif keyword_count >= 1:  # Al menos un término técnico
            confidence = 0.2 + language_bonus
        else:
            confidence = 0.0

        logger.info(
            "programming_confidence_calculated",
            agent_id=self.agent_id,
            keyword_count=keyword_count,
            language_count=language_count,
            density=density,
            has_code=has_code,
            confidence=confidence,
        )

        return confidence

    async def process_query(
        self, query: str, context: Optional[Dict] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Procesa consultas de programación y retorna análisis estructurado.
        """
        import time

        start_time = time.time()

        try:
            self.record_activation()

            # Análisis de la consulta
            analysis = self._analyze_programming_query(query)

            # Generar respuesta estructurada
            response = {
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "specialty": self.specialty,
                "confidence": self.can_handle(query, context),
                "query_analysis": analysis,
                "code_analysis": self._analyze_code_snippets(query),
                "recommendations": self._generate_programming_recommendations(analysis),
                "best_practices": self._suggest_best_practices(analysis),
                "resources": self._suggest_resources(analysis),
            }

            response_time = time.time() - start_time
            self.record_success(response_time)

            logger.info(
                "programming_query_processed",
                agent_id=self.agent_id,
                response_time=response_time,
            )

            return response

        except Exception as e:
            response_time = time.time() - start_time
            self.record_failure()

            logger.error(
                "programming_query_failed",
                agent_id=self.agent_id,
                error=str(e),
                response_time=response_time,
            )

            return {
                "agent_id": self.agent_id,
                "error": f"Error procesando consulta de programación: {str(e)}",
                "confidence": 0.0,
            }

    def _analyze_programming_query(self, query: str) -> Dict[str, Any]:
        """Analiza la consulta de programación."""
        analysis = {
            "query_type": "unknown",
            "languages": [],
            "topics": [],
            "difficulty": "medium",
            "has_code": False,
            "code_snippets": [],
        }

        query_lower = query.lower()

        # Detectar lenguajes
        languages = [
            "python",
            "javascript",
            "java",
            "c++",
            "php",
            "ruby",
            "go",
            "rust",
            "typescript",
            "sql",
        ]
        for lang in languages:
            if re.search(r"\b" + lang + r"\b", query_lower):
                analysis["languages"].append(lang)

        # Detectar código
        if "```" in query or any(
            keyword in query_lower
            for keyword in ["def ", "class ", "function", "import "]
        ):
            analysis["has_code"] = True
            # Extraer snippets de código básicos
            code_blocks = re.findall(r"```(?:\w+)?\n(.*?)\n```", query, re.DOTALL)
            analysis["code_snippets"] = code_blocks

        # Clasificar tipo de consulta
        if any(
            word in query_lower for word in ["error", "bug", "problema", "no funciona"]
        ):
            analysis["query_type"] = "debugging"
        elif any(
            word in query_lower for word in ["cómo", "como", "tutorial", "aprender"]
        ):
            analysis["query_type"] = "learning"
        elif any(word in query_lower for word in ["optimiz", "performance", "mejorar"]):
            analysis["query_type"] = "optimization"
        elif any(
            word in query_lower for word in ["diseño", "arquitectura", "estructura"]
        ):
            analysis["query_type"] = "architecture"
        elif analysis["has_code"]:
            analysis["query_type"] = "code_review"

        # Identificar tópicos
        topics_keywords = {
            "algorithms": ["algoritmo", "algorithm", "sort", "search", "complexity"],
            "data_structures": ["array", "list", "dict", "tree", "graph", "hash"],
            "web_dev": ["html", "css", "javascript", "react", "vue", "angular", "api"],
            "databases": ["sql", "mysql", "postgresql", "mongodb", "orm"],
            "testing": ["test", "unit", "integration", "tdd", "pytest", "junit"],
            "version_control": ["git", "github", "merge", "branch", "commit"],
        }

        for topic, keywords in topics_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                analysis["topics"].append(topic)

        # Determinar dificultad
        if analysis["query_type"] == "debugging" and analysis["has_code"]:
            analysis["difficulty"] = "high"
        elif len(analysis["topics"]) > 2 or len(analysis["languages"]) > 1:
            analysis["difficulty"] = "high"
        elif analysis["has_code"] or analysis["query_type"] in [
            "architecture",
            "optimization",
        ]:
            analysis["difficulty"] = "medium"
        else:
            analysis["difficulty"] = "low"

        return analysis

    def _analyze_code_snippets(self, query: str) -> Dict[str, Any]:
        """Analiza snippets de código en la consulta."""
        analysis = {
            "snippets_found": 0,
            "languages_detected": [],
            "potential_issues": [],
            "quality_score": 0.0,
        }

        # Buscar bloques de código
        code_blocks = re.findall(r"```(?:\w+)?\n(.*?)\n```", query, re.DOTALL)
        analysis["snippets_found"] = len(code_blocks)

        if not code_blocks:
            return analysis

        # Análisis básico de cada bloque
        for i, block in enumerate(code_blocks):
            block_lower = block.lower()

            # Detectar lenguaje
            if "def " in block or "import " in block or "print(" in block:
                if "python" not in analysis["languages_detected"]:
                    analysis["languages_detected"].append("python")
            elif "function" in block or "console.log" in block:
                if "javascript" not in analysis["languages_detected"]:
                    analysis["languages_detected"].append("javascript")
            elif "public class" in block or "system.out.println" in block:
                if "java" not in analysis["languages_detected"]:
                    analysis["languages_detected"].append("java")

            # Detectar problemas comunes
            issues = []
            if "==" in block and "null" in block_lower:  # Python None comparison
                issues.append("Posible comparación incorrecta con None (usar is)")
            if (
                "except:" in block and ":" not in block.split("except:")[1][:50]
            ):  # Bare except
                issues.append("Uso de except vacío (muy amplio)")
            if len(block.split("\n")) > 50:  # Long function
                issues.append("Función muy larga (considerar dividir)")

            analysis["potential_issues"].extend(
                [f"Snippet {i+1}: {issue}" for issue in issues]
            )

        # Calcular score de calidad básico
        total_lines = sum(len(block.split("\n")) for block in code_blocks)
        has_comments = any("# " in block or "// " in block for block in code_blocks)
        has_functions = any(
            "def " in block or "function" in block for block in code_blocks
        )

        score = 0.5  # Base
        if has_comments:
            score += 0.2
        if has_functions:
            score += 0.2
        if total_lines < 20:
            score += 0.1
        elif total_lines > 100:
            score -= 0.2

        analysis["quality_score"] = max(0.0, min(1.0, score))

        return analysis

    def _generate_programming_recommendations(
        self, analysis: Dict[str, Any]
    ) -> List[str]:
        """Genera recomendaciones basadas en el análisis."""
        recommendations = []

        query_type = analysis.get("query_type", "unknown")
        languages = analysis.get("languages", [])
        difficulty = analysis.get("difficulty", "medium")

        # Recomendaciones por tipo de consulta
        if query_type == "debugging":
            recommendations.extend(
                [
                    "Revisa los mensajes de error completos y el stack trace",
                    "Usa un debugger para ejecutar el código paso a paso",
                    "Agrega logging/print statements para rastrear el flujo",
                    "Verifica tipos de datos y valores de variables en puntos críticos",
                ]
            )
        elif query_type == "learning":
            recommendations.extend(
                [
                    "Comienza con proyectos pequeños y aumenta gradualmente la complejidad",
                    "Lee documentación oficial y ejemplos prácticos",
                    "Practica con ejercicios en plataformas como LeetCode o HackerRank",
                    "Únete a comunidades de programadores para hacer preguntas",
                ]
            )
        elif query_type == "code_review":
            recommendations.extend(
                [
                    "Revisa la lógica del algoritmo antes de la sintaxis",
                    "Verifica manejo de casos edge y errores",
                    "Considera legibilidad y mantenibilidad del código",
                    "Ejecuta pruebas unitarias para validar funcionalidad",
                ]
            )
        elif query_type == "optimization":
            recommendations.extend(
                [
                    "Usa profiling tools para identificar cuellos de botella",
                    "Considera complejidad algorítmica (Big O)",
                    "Optimiza uso de memoria y estructuras de datos",
                    "Mide performance antes y después de cambios",
                ]
            )
        elif query_type == "architecture":
            recommendations.extend(
                [
                    "Sigue principios SOLID y DRY",
                    "Documenta decisiones arquitectónicas importantes",
                    "Considera escalabilidad y mantenibilidad futura",
                    "Usa patrones de diseño apropiados para el problema",
                ]
            )

        # Recomendaciones por lenguaje
        if "python" in languages:
            recommendations.extend(
                [
                    "Sigue PEP 8 para estilo de código",
                    "Usa type hints para mejor documentación",
                    "Considera virtual environments para aislamiento",
                ]
            )
        elif "javascript" in languages:
            recommendations.extend(
                [
                    "Usa ESLint para mantener calidad de código",
                    "Considera TypeScript para proyectos grandes",
                    "Aprende sobre asincronía y promises",
                ]
            )

        # Recomendaciones por dificultad
        if difficulty == "high":
            recommendations.insert(
                0, "🔴 COMPLEJO: Divide el problema en partes más pequeñas"
            )
        elif difficulty == "low":
            recommendations.append("🟢 SENCILLO: ¡Excelente oportunidad para aprender!")

        # Recomendaciones generales
        if not recommendations:
            recommendations = [
                "Define claramente el problema antes de programar",
                "Piensa en el algoritmo antes de escribir código",
                "Escribe código legible y bien documentado",
                "Prueba tu código con diferentes casos de entrada",
            ]

        return recommendations

    def _suggest_best_practices(self, analysis: Dict[str, Any]) -> List[str]:
        """Sugiere mejores prácticas basadas en el análisis."""
        practices = []

        languages = analysis.get("languages", [])
        topics = analysis.get("topics", [])

        # Prácticas generales
        practices.extend(
            [
                "Escribe código autodocumentado con nombres descriptivos",
                "Sigue convenciones del lenguaje (PEP 8, Airbnb style, etc.)",
                "Implementa manejo de errores apropiado",
                "Escribe pruebas para validar funcionalidad",
            ]
        )

        # Prácticas por lenguaje
        if "python" in languages:
            practices.extend(
                [
                    "Usa list comprehensions para código más conciso",
                    "Aprovecha las baterías incluidas de Python",
                    "Sigue principio EAFP (Es más fácil pedir perdón que permiso)",
                ]
            )
        elif "javascript" in languages:
            practices.extend(
                [
                    "Usa const/let en lugar de var",
                    "Aprende sobre closures y scope",
                    "Evita callback hell usando async/await",
                ]
            )

        # Prácticas por tópico
        if "testing" in topics:
            practices.extend(
                [
                    "Escribe tests antes del código (TDD)",
                    "Cubre casos normales, edge cases y errores",
                    "Mantén tests independientes y rápidos",
                ]
            )
        elif "version_control" in topics:
            practices.extend(
                [
                    "Haz commits pequeños y frecuentes",
                    "Escribe mensajes de commit descriptivos",
                    "Usa branches para features nuevas",
                ]
            )

        return practices

    def _suggest_resources(self, analysis: Dict[str, Any]) -> List[str]:
        """Sugiere recursos de aprendizaje."""
        resources = []

        languages = analysis.get("languages", [])
        topics = analysis.get("topics", [])
        query_type = analysis.get("query_type", "unknown")

        # Recursos por lenguaje
        if "python" in languages:
            resources.extend(
                [
                    '📚 "Automate the Boring Stuff with Python" - libro gratuito',
                    "🎯 Python.org documentation",
                    "💡 Real Python tutorials",
                ]
            )
        elif "javascript" in languages:
            resources.extend(
                [
                    '📚 "Eloquent JavaScript" - libro gratuito',
                    "🎯 MDN Web Docs",
                    "💡 JavaScript.info tutorials",
                ]
            )

        # Recursos por tópico
        if "algorithms" in topics:
            resources.extend(
                [
                    '📚 "Introduction to Algorithms" - CLRS',
                    "🎯 GeeksforGeeks y LeetCode",
                    "💡 VisuAlgo para visualización",
                ]
            )
        elif "web_dev" in topics:
            resources.extend(
                [
                    '📚 "HTML and CSS" de Jon Duckett',
                    "🎯 freeCodeCamp curriculum",
                    "💡 MDN Web Docs",
                ]
            )

        # Recursos por tipo de consulta
        if query_type == "debugging":
            resources.extend(
                [
                    "🔧 Python Debugger (pdb)",
                    "🔧 Chrome DevTools para JavaScript",
                    "💡 Stack Overflow debugging guides",
                ]
            )

        # Recursos generales si no hay específicos
        if not resources:
            resources = [
                "📚 Documentación oficial del lenguaje",
                "🎯 Stack Overflow para preguntas específicas",
                "💡 GitHub para ver código de proyectos reales",
                "👥 Comunidades como Reddit r/learnprogramming",
            ]

        return resources
