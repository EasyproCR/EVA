"""
Query Preprocessor - Detecta patrones específicos en consultas del usuario
para enrutarlas directamente a la herramienta correcta sin pasar por el selector LLM
"""

import re
import logging
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Tipos de consulta detectables"""
    PROPERTY_ID = "property_id"  # Consulta con ID de propiedad específico
    GENERAL = "general"           # Consulta general (usa router)


class QueryPreprocessor:
    """
    Pre-procesa consultas para detectar patrones y enrutarlas directamente.

    Uso:
        preprocessor = QueryPreprocessor()
        query_type, property_id = preprocessor.analyze("¿Cuál es el precio de la propiedad 59338?")

        if query_type == QueryType.PROPERTY_ID:
            # Enruta directamente a property_info
            response = property_info_tool.query(query)
        else:
            # Pasa al router normal
            response = router.query(query)
    """

    def analyze(self, query: str) -> Tuple[QueryType, Optional[int]]:
        """
        Analiza una consulta y detecta el tipo y parámetros.

        Returns:
            Tuple[QueryType, Optional[int]]: (tipo_consulta, property_id si aplica)
        """
        query_lower = query.lower()

        # Detectar si tiene ID de propiedad
        property_id = self._extract_property_id(query_lower)
        if property_id is not None:
            logger.info(f"  🔍 PreProcessor: Detectado ID de propiedad: {property_id}")

            # Validar que sea una consulta sobre la propiedad específica
            # (no solo que mencione un ID aislado)
            if self._is_property_question(query_lower):
                logger.info(f"  ✓ Consulta sobre propiedad → EnrutandoDirecto a property_info")
                return QueryType.PROPERTY_ID, property_id

        # Si no detectó patrón específico, usa router normal
        return QueryType.GENERAL, None

    def _extract_property_id(self, query_lower: str) -> Optional[int]:
        """
        Extrae ID de propiedad del query.
        Detecta patrones como:
        - "ID: 123" o "id: 123"
        - "ID 123"
        - "#ID 123"
        - "propiedad 123"
        - "propiedades 123" (no confundir con "propiedades en...")

        Returns:
            int: ID de la propiedad o None
        """
        # Patrón 1: "ID: 123" o "id: 123" o "ID=123"
        match = re.search(r'\bid\s*[:=]?\s*(\d+)\b', query_lower)
        if match:
            return int(match.group(1))

        # Patrón 2: "propiedad 123" (pero NO "propiedades en..." o "propiedades de...")
        # Usa lookahead negativo para evitar false positives
        match = re.search(r'\bpropiedad(?:es)?\s+(?!en\b|de\b|del\b|para)(\d+)\b', query_lower)
        if match:
            return int(match.group(1))

        # Patrón 3: "#ID 123" o "# 123"
        match = re.search(r'#\s*(?:id\s+)?(\d+)\b', query_lower)
        if match:
            return int(match.group(1))

        return None

    def _is_property_question(self, query_lower: str) -> bool:
        """
        Valida que la consulta sea realmente sobre propiedades específicas,
        no solo que mencione un número.

        Busca palabras clave que indiquen una consulta sobre propiedades.
        """
        # Palabras clave que indican consulta sobre propiedades
        property_keywords = [
            'propiedad', 'información', 'información', 'dime', 'dame', 'detalles',
            'precio', 'costo', 'banco', 'agente', 'ubicación', 'habitaciones',
            'baños', 'área', 'tamaño', 'características', 'tipo', 'brindar',
            'cuál', 'cuales', 'cual', 'cuales', 'quien', 'quién', 'donde', 'dónde'
        ]

        for keyword in property_keywords:
            if keyword in query_lower:
                return True

        return False


# Singleton instance
_preprocessor_instance = None


def get_preprocessor() -> QueryPreprocessor:
    """Obtiene la instancia singleton del preprocessor."""
    global _preprocessor_instance
    if _preprocessor_instance is None:
        _preprocessor_instance = QueryPreprocessor()
    return _preprocessor_instance
