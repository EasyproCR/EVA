"""
Property Reference Detector - Módulo modular para detección de referencias contextuales
Extrae y maneja referencias a propiedades mencionadas en el historial de chat
"""

import re
import logging
from typing import Optional, List
from llama_index.core.llms import ChatMessage

logger = logging.getLogger(__name__)


class PropertyReferenceDetector:
    """
    Detecta cuando el usuario hace referencia a propiedades mostradas previamente
    y extrae la URL correspondiente para análisis detallado.
    
    Uso:
        detector = PropertyReferenceDetector()
        modified_msg = detector.detect_and_modify(mensaje, chat_history)
    """
    
    # Patrones que indican solicitud de más detalles
    DETAIL_PATTERNS = [
        r'\b(?:dime|dame|quiero|necesito|muestra|ver)\s+(?:más|mas|info|información|detalles?)\b',
        r'\b(?:sobre|de|del)\s+(?:la|el|esa|ese|esta|este)\b',
        r'\b(?:ampliar|expandir|profundiza|profundizar)\b',
        r'\b(?:primera?|segunda?|tercera?|[0-9]+[aº°]?)\b',
        r'\b#[0-9]+\b',
    ]
    
    # Ordinales en español
    ORDINALS = {
        'primer': 1, 'primera': 1, 'primero': 1,
        'segund': 2, 'segunda': 2, 'segundo': 2,
        'tercer': 3, 'tercera': 3, 'tercero': 3,
        'cuart': 4, 'cuarta': 4, 'cuarto': 4,
        'quint': 5, 'quinta': 5, 'quinto': 5,
        'sext': 6, 'sexta': 6, 'sexto': 6,
    }
    
    def detect_and_modify(
        self, 
        mensaje: str, 
        chat_history: List[ChatMessage]
    ) -> str:
        """
        Detecta referencias contextuales y modifica el mensaje si es necesario.
        
        Args:
            mensaje: Mensaje original del usuario
            chat_history: Historial de mensajes (últimos N turnos)
            
        Returns:
            str: Mensaje original o modificado con URL si se detectó referencia
        """
        # 1. Detectar si es solicitud de detalles
        if not self._is_detail_request(mensaje):
            return mensaje
        
        logger.info("🔍 Detectada solicitud de detalles de propiedad")
        
        # 2. Extraer URLs del historial
        urls = self._extract_urls_from_history(chat_history)
        
        if not urls:
            logger.info("⚠️ No se encontraron URLs de propiedades en el historial")
            return mensaje
        
        logger.info(f"✓ Encontradas {len(urls)} URLs en historial")
        
        # 3. Detectar número de referencia
        number_ref = self._extract_number_reference(mensaje)
        
        # 4. Seleccionar URL apropiada
        target_url = self._select_url(urls, number_ref)
        
        if not target_url:
            return mensaje
        
        # 5. Modificar mensaje para forzar uso de Tavily
        modified_msg = f"Dame información detallada de {target_url}"
        
        logger.info(f"✓ Mensaje modificado para Tavily")
        logger.info(f"  Original: '{mensaje}'")
        logger.info(f"  Modificado: '{modified_msg}'")
        
        return modified_msg
    
    def _is_detail_request(self, mensaje: str) -> bool:
        """Verifica si el mensaje solicita más detalles."""
        mensaje_lower = mensaje.lower()
        
        for pattern in self.DETAIL_PATTERNS:
            if re.search(pattern, mensaje_lower):
                return True
        
        return False
    
    def _extract_urls_from_history(
        self, 
        chat_history: List[ChatMessage]
    ) -> List[str]:
        """
        Extrae URLs de propiedades del historial (solo mensajes del asistente).
        
        Returns:
            List[str]: URLs únicas en orden (más reciente primero)
        """
        urls = []
        
        # Revisar mensajes del asistente (en orden inverso = más recientes primero)
        for msg in reversed(chat_history):
            if msg.role != "assistant":
                continue
            
            # Buscar URLs de bienesadjudicadoscr.com
            found = re.findall(
                r'https?://bienesadjudicadoscr\.com/propiedades/[^\s)\]]+',
                msg.content,
                re.IGNORECASE
            )
            urls.extend(found)
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_urls = [url for url in urls if not (url in seen or seen.add(url))]
        
        return unique_urls
    
    def _extract_number_reference(self, mensaje: str) -> Optional[int]:
        """
        Extrae referencia numerada del mensaje.
        
        Args:
            mensaje: Mensaje del usuario
            
        Returns:
            Optional[int]: Número de la propiedad (1-indexed) o None
        """
        # Patrón #N
        match = re.search(r'#([0-9]+)', mensaje)
        if match:
            num = int(match.group(1))
            logger.info(f"✓ Detectada referencia: #{num}")
            return num
        
        # Patrón "primera", "segundo", etc.
        msg_lower = mensaje.lower()
        for key, num in self.ORDINALS.items():
            if key in msg_lower:
                logger.info(f"✓ Detectada referencia ordinal: {key} -> {num}")
                return num
        
        # Patrón "el 1", "el 2", etc.
        match = re.search(r'\b(?:la|el|número|numero|num)\s+([0-9]+)', msg_lower)
        if match:
            num = int(match.group(1))
            logger.info(f"✓ Detectada referencia numérica: el/la {num}")
            return num
        
        return None
    
    def _select_url(
        self, 
        urls: List[str], 
        number_ref: Optional[int] = None
    ) -> Optional[str]:
        """
        Selecciona la URL apropiada basado en la referencia.
        
        Args:
            urls: Lista de URLs disponibles (más reciente primero)
            number_ref: Referencia numérica (1-indexed) o None
            
        Returns:
            Optional[str]: URL seleccionada o None
        """
        if not urls:
            return None
        
        # Si hay número, usar ese índice
        if number_ref is not None:
            index = number_ref - 1  # Convertir a 0-indexed
            if 0 <= index < len(urls):
                logger.info(f"✓ URL seleccionada por número: {urls[index]}")
                return urls[index]
            else:
                logger.warning(f"⚠️ Número {number_ref} fuera de rango (hay {len(urls)} propiedades)")
                return None
        
        # Por defecto, la más reciente (primera)
        logger.info(f"✓ URL por defecto (más reciente): {urls[0]}")
        return urls[0]


# ============================================================================
# FUNCIÓN DE CONVENIENCIA PARA USAR EN EL ORCHESTRATOR
# ============================================================================

# Instancia global reutilizable
_detector = PropertyReferenceDetector()


def detect_property_reference(
    mensaje: str, 
    chat_history: List[ChatMessage]
) -> str:
    """
    Función de conveniencia para detectar y modificar referencias.
    
    Esta es la función que debes llamar desde el orchestrator.
    
    Args:
        mensaje: Mensaje del usuario
        chat_history: Historial de chat (últimos 10 mensajes)
        
    Returns:
        str: Mensaje original o modificado si se detectó referencia
        
    Example:
        mensaje_procesado = detect_property_reference(mensaje, chat_history)
        # Si no hay referencia: retorna mensaje original
        # Si hay referencia: retorna "Dame información detallada de [URL]"
    """
    return _detector.detect_and_modify(mensaje, chat_history)


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Mock de historial de chat con URLs
    from llama_index.core.llms import ChatMessage
    
    mock_history = [
        ChatMessage(
            role="assistant",
            content="""
            Resultados:
            
            1. Terreno en Moravia | USD 450,000 | https://bienesadjudicadoscr.com/propiedades/terreno-moravia-1
            2. Casa en Escazú | USD 380,000 | https://bienesadjudicadoscr.com/propiedades/casa-escazu-2
            3. Lote en Guanacaste | USD 200,000 | https://bienesadjudicadoscr.com/propiedades/lote-guanacaste-3
            """
        )
    ]
    
    # Test cases
    test_cases = [
        ("Dime más sobre la primera", "Debe detectar #1"),
        ("Info de #2", "Debe detectar #2"),
        ("Detalles del tercero", "Debe detectar #3"),
        ("Dame más información", "Debe tomar la primera por defecto"),
        ("Casas en San José", "NO debe detectar (búsqueda nueva)"),
    ]
    
    print("\n" + "="*80)
    print("TESTS DE DETECCIÓN")
    print("="*80 + "\n")
    
    detector = PropertyReferenceDetector()
    
    for mensaje, descripcion in test_cases:
        print(f"Test: {descripcion}")
        print(f"Input: '{mensaje}'")
        
        result = detector.detect_and_modify(mensaje, mock_history)
        
        if result != mensaje:
            print(f"✓ DETECTADO - Output: '{result[:60]}...'")
        else:
            print(f"○ NO DETECTADO - Output: '{result}'")
        
        print("-" * 80)