"""
Conversation Context Manager - Mantiene estado conversacional
Gestiona el contexto de la última propiedad mencionada y detecta referencias implícitas
"""

import re
import logging
from typing import Optional, Dict, Any, List
from llama_index.core.llms import ChatMessage

logger = logging.getLogger(__name__)


class ConversationContext:
    """
    Mantiene el contexto conversacional por sesión.
    Rastrea la última propiedad mencionada para responder preguntas contextuales.
    """
    
    def __init__(self):
        # {session_id: {last_property: {...}, last_search_results: [...]}}
        self.sessions = {}
    
    def update_last_property(
        self, 
        session_id: str, 
        property_data: Dict[str, Any]
    ):
        """
        Actualiza la última propiedad mencionada en la sesión.
        
        Args:
            session_id: ID de sesión del usuario
            property_data: Datos de la propiedad (nombre, url, precio, banco, etc.)
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        
        self.sessions[session_id]['last_property'] = property_data
        logger.info(f"✓ Contexto actualizado - Última propiedad: {property_data.get('nombre', 'N/A')}")
    
    def update_search_results(
        self,
        session_id: str,
        results: List[Dict[str, Any]]
    ):
        """
        Actualiza los resultados de la última búsqueda.
        
        Args:
            session_id: ID de sesión
            results: Lista de propiedades encontradas
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        
        self.sessions[session_id]['last_search_results'] = results
        logger.info(f"✓ Resultados de búsqueda guardados: {len(results)} propiedades")
    
    def get_last_property(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene la última propiedad mencionada."""
        if session_id not in self.sessions:
            return None
        return self.sessions[session_id].get('last_property')
    
    def get_search_results(self, session_id: str) -> List[Dict[str, Any]]:
        """Obtiene los resultados de la última búsqueda."""
        if session_id not in self.sessions:
            return []
        return self.sessions[session_id].get('last_search_results', [])
    
    def detect_contextual_question(
        self,
        mensaje: str,
        session_id: str
    ) -> Optional[str]:
        """
        Detecta preguntas contextuales sobre la última propiedad.
        
        Args:
            mensaje: Pregunta del usuario
            session_id: ID de sesión
            
        Returns:
            Optional[str]: Mensaje expandido con contexto, o None si no aplica
        """
        # Patrones de preguntas contextuales
        contextual_patterns = [
            r'\b(?:a\s+(?:que|qué|cual)\s+banco)\b',           # "a que banco"
            r'\b(?:de\s+(?:que|qué|cual)\s+banco)\b',          # "de que banco"
            r'\b(?:quien|quién)\s+(?:es\s+el\s+)?(?:dueño|propietario|vendedor)\b',
            r'\b(?:cual|cuál)\s+es\s+(?:el|la)\s+(?:precio|ubicación|dirección)\b',
            r'\b(?:tiene|incluye)\s+\w+\b',                    # "tiene garage"
            r'\b(?:cuantos|cuántos)\s+(?:cuartos|habitaciones|baños)\b',
            r'\b(?:donde|dónde)\s+(?:esta|está|queda)\b',
        ]
        
        mensaje_lower = mensaje.lower()
        
        # Verificar si es pregunta contextual
        is_contextual = any(re.search(pattern, mensaje_lower) for pattern in contextual_patterns)
        
        if not is_contextual:
            return None
        
        # Obtener última propiedad
        last_prop = self.get_last_property(session_id)
        
        if not last_prop:
            logger.info("⚠️ Pregunta contextual pero no hay propiedad previa")
            return None
        
        # Expandir pregunta con contexto
        prop_name = last_prop.get('nombre', 'la propiedad')
        prop_url = last_prop.get('property_url', '')
        
        logger.info(f"🔍 Detectada pregunta contextual sobre: {prop_name}")
        
        # Construir pregunta expandida
        if prop_url:
            expanded = f"{mensaje} de la propiedad '{prop_name}' ({prop_url})"
        else:
            expanded = f"{mensaje} de la propiedad '{prop_name}'"
        
        logger.info(f"  Original: '{mensaje}'")
        logger.info(f"  Expandido: '{expanded}'")
        
        return expanded


# Instancia global
_context_manager = ConversationContext()


def update_property_context(session_id: str, property_data: Dict[str, Any]):
    """Actualiza el contexto de la última propiedad mostrada."""
    _context_manager.update_last_property(session_id, property_data)


def update_search_context(session_id: str, results: List[Dict[str, Any]]):
    """Actualiza el contexto de los últimos resultados de búsqueda."""
    _context_manager.update_search_results(session_id, results)


def expand_contextual_question(mensaje: str, session_id: str) -> str:
    """
    Expande preguntas contextuales con información de la última propiedad.
    
    Args:
        mensaje: Mensaje original del usuario
        session_id: ID de sesión
        
    Returns:
        str: Mensaje expandido si es contextual, original si no
    """
    expanded = _context_manager.detect_contextual_question(mensaje, session_id)
    return expanded if expanded else mensaje


def get_last_property_data(session_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene datos de la última propiedad mencionada."""
    return _context_manager.get_last_property(session_id)


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Simular contexto de sesión
    session = "test-123"
    
    # 1. Actualizar con una propiedad
    prop_data = {
        'nombre': 'Casa en El Carmen',
        'property_url': 'https://bienesadjudicadoscr.com/propiedades/casa-carmen-123',
        'precio_usd': 144914,
        'banco': 'Banco Nacional'
    }
    
    update_property_context(session, prop_data)
    
    # 2. Probar detección contextual
    test_questions = [
        ("a que banco pertenece?", True),
        ("cual es el precio?", True),
        ("tiene garage?", True),
        ("donde esta ubicada?", True),
        ("busca casas en San José", False),  # No contextual
    ]
    
    print("\n" + "="*80)
    print("TESTS DE DETECCIÓN CONTEXTUAL")
    print("="*80 + "\n")
    
    for question, should_expand in test_questions:
        expanded = expand_contextual_question(question, session)
        
        if expanded != question:
            print(f"✓ EXPANDIDO")
            print(f"  Original:  '{question}'")
            print(f"  Expandido: '{expanded}'")
        else:
            print(f"○ SIN CAMBIOS: '{question}'")
        
        print("-" * 80)