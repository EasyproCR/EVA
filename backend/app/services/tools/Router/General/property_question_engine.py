"""
Property Question Answering Engine - Responde preguntas sobre propiedades desde BD
Para preguntas específicas como "a que banco pertenece?" sin necesidad de web crawling
"""

import re
import logging
from typing import Optional, Dict, Any

from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from llama_index.core import Settings

logger = logging.getLogger(__name__)


class PropertyQuestionEngine(BaseQueryEngine):
    """
    Query Engine para responder preguntas específicas sobre propiedades.
    
    Uso:
        - "a que banco pertenece?"
        - "quien es el agente?"
        - "cual es el precio?"
        - "cuantas habitaciones tiene?"
    
    Busca la respuesta directamente en la BD sin necesidad de crawlear la web.
    """
    
    def __init__(self, property_db_service, context_manager):
        """
        Args:
            property_db_service: PropertyDatabaseService instance
            context_manager: ConversationContext para obtener última propiedad
        """
        super().__init__(callback_manager=CallbackManager([]))
        self.context_manager = context_manager
        self.property_db_service = property_db_service
        logger.info("✓ PropertyQuestionEngine inicializado")
    
    def _query(self, query_bundle: QueryBundle) -> Response:
        """
        Responde preguntas sobre propiedades desde la BD.
        """
        query = query_bundle.query_str
        logger.info(f"📋 Pregunta sobre propiedad: {query}")
        
        # Detectar tipo de pregunta
        question_type = self._detect_question_type(query)
        
        if not question_type:
            return Response(
                response="No estoy seguro de qué información necesitas sobre la propiedad. "
                "¿Podrías ser más específico?"
            )
        
        logger.info(f"  Tipo detectado: {question_type}")
        
        # Obtener datos de la propiedad
        # Intentar extraer URL del query
        urls = re.findall(r'https?://\S+', query)
        property_data = None
        
        if urls:
            # Si hay URL en el query, buscar por URL
            property_data = self.property_db_service.get_property_by_url(urls[0])
        else:
            # Si no, buscar por nombre en el query
            # Extraer posible nombre de propiedad
            name_match = re.search(r'(?:de|del|sobre)\s+["\']?([^"\'?]+)["\']?', query, re.IGNORECASE)
            if name_match:
                property_name = name_match.group(1).strip()
                property_data = self.property_db_service.get_property_by_name(property_name)
        
        if not property_data:
            return Response(
                response=(
                    "No encontré información de esa propiedad en nuestra base de datos. "
                    "¿Podrías proporcionar el enlace de la propiedad o más detalles?"
                )
            )
        
        # Generar respuesta según el tipo de pregunta
        response_text = self._generate_answer(question_type, property_data)
        
        return Response(response=response_text)
    
    def _detect_question_type(self, query: str) -> Optional[str]:
        """
        Detecta qué tipo de pregunta es.
        
        Returns:
            str: Tipo de pregunta o None
        """
        query_lower = query.lower()
        
        # Banco/Entidad
        if re.search(r'\b(banco|entidad|institution|financiera)\b', query_lower):
            return 'banco'
        
        # Agente
        if re.search(r'\b(agente|asesor|encargado|contacto|representante)\b', query_lower):
            return 'agente'
        
        # Precio
        if re.search(r'\b(precio|costo|cuanto\s+cuesta|valor)\b', query_lower):
            return 'precio'
        
        # Habitaciones
        if re.search(r'\b(habitacion|cuarto|dormitorio|bedroom)\b', query_lower):
            return 'habitaciones'
        
        # Baños
        if re.search(r'\b(baño|bathroom)\b', query_lower):
            return 'banos'
        
        # Ubicación
        if re.search(r'\b(ubicacion|ubicada|direccion|donde|queda|esta)\b', query_lower):
            return 'ubicacion'
        
        # Área/Tamaño
        if re.search(r'\b(area|tamaño|tamano|metros|m2|grande)\b', query_lower):
            return 'area'
        
        # Tipo
        if re.search(r'\b(tipo|categoria|clase)\b', query_lower):
            return 'tipo'
        
        return None
    
    def _generate_answer(
        self,
        question_type: str,
        property_data: Dict[str, Any]
    ) -> str:
        """
        Genera respuesta específica según el tipo de pregunta.
        """
        prop_name = property_data.get('nombre', 'La propiedad')
        
        if question_type == 'banco':
            banco = property_data.get('nombre_banco')
            if banco:
                return (
                    f"**{prop_name}** pertenece a **{banco}**.\n\n"
                    f"Para más información sobre el proceso de adquisición, "
                    f"te recomiendo contactar directamente con el banco o el agente a cargo."
                )
            else:
                return f"No tengo información del banco para **{prop_name}** en nuestra base de datos."
        
        elif question_type == 'agente':
            agent_name = property_data.get('agent_name')
            agent_phone = property_data.get('agent_phone_number')
            
            if agent_name:
                response = f"El agente a cargo de **{prop_name}** es **{agent_name}**"
                if agent_phone:
                    response += f" 📞 **{agent_phone}**"
                response += ".\n\n¿Necesitas que te ayude con algo más sobre esta propiedad?"
                return response
            else:
                return f"No tengo información del agente para **{prop_name}** en nuestra base de datos."
        
        elif question_type == 'precio':
            precio = property_data.get('precio_usd')
            if precio:
                return (
                    f"El precio de **{prop_name}** es **USD {precio:,.0f}**.\n\n"
                    f"Este precio puede estar sujeto a negociación dependiendo del banco/entidad. "
                    f"¿Te gustaría conocer más detalles sobre esta propiedad?"
                )
            else:
                return (
                    f"El precio de **{prop_name}** no está disponible en nuestra base de datos. "
                    f"Te recomiendo contactar al agente directamente para obtener información actualizada."
                )
        
        elif question_type == 'habitaciones':
            bedrooms = property_data.get('bedrooms')
            if bedrooms:
                return f"**{prop_name}** tiene **{bedrooms} habitaciones**."
            else:
                return f"No tengo información sobre el número de habitaciones de **{prop_name}**."
        
        elif question_type == 'banos':
            bathrooms = property_data.get('bathrooms')
            if bathrooms:
                return f"**{prop_name}** tiene **{bathrooms} baños**."
            else:
                return f"No tengo información sobre el número de baños de **{prop_name}**."
        
        elif question_type == 'ubicacion':
            ubicacion_parts = []
            if property_data.get('distrito'):
                ubicacion_parts.append(property_data['distrito'])
            if property_data.get('canton'):
                ubicacion_parts.append(property_data['canton'])
            if property_data.get('provincia'):
                ubicacion_parts.append(property_data['provincia'])
            
            if ubicacion_parts:
                ubicacion = ', '.join(ubicacion_parts)
                return (
                    f"**{prop_name}** está ubicada en **{ubicacion}**.\n\n"
                    f"¿Te gustaría conocer más detalles sobre la zona o la propiedad?"
                )
            else:
                return f"No tengo información detallada de la ubicación de **{prop_name}**."
        
        elif question_type == 'area':
            area_const = property_data.get('area_construccion')
            area_lote = property_data.get('tamanio_lote')
            
            response = f"**{prop_name}**:"
            
            if area_const:
                response += f"\n• Área de construcción: **{area_const} m²**"
            if area_lote:
                response += f"\n• Tamaño del lote: **{area_lote} m²**"
            
            if not area_const and not area_lote:
                response = f"No tengo información sobre las áreas de **{prop_name}**."
            
            return response
        
        elif question_type == 'tipo':
            tipo = property_data.get('tipo_propiedad')
            if tipo:
                return f"**{prop_name}** es un/a **{tipo}**."
            else:
                return f"No tengo información sobre el tipo de **{prop_name}**."
        
        return "No pude encontrar esa información específica."
    
    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        """Versión async."""
        return self._query(query_bundle)
    
    def _get_prompt_modules(self):
        """Requerido por BaseQueryEngine."""
        return {}


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Mock de datos de propiedad
    mock_property = {
        'nombre': 'Casa en El Carmen',
        'provincia': 'Cartago',
        'canton': 'Cartago',
        'distrito': 'El Carmen',
        'precio_usd': 144914,
        'bedrooms': 3,
        'bathrooms': 2,
        'nombre_banco': 'Banco Nacional',
        'agent_name': 'Juan Pérez',
        'agent_phone_number': '+506 1234-5678',
        'tipo_propiedad': 'Casa'
    }
    
    # Simular preguntas
    test_questions = [
        "a que banco pertenece?",
        "quien es el agente?",
        "cual es el precio?",
        "cuantas habitaciones tiene?",
        "donde esta ubicada?",
    ]
    
    print("\n" + "="*80)
    print("TESTS DE PREGUNTAS SOBRE PROPIEDADES")
    print("="*80 + "\n")
    
    # Mock de DB service
    class MockDBService:
        def get_property_by_url(self, url):
            return mock_property
        def get_property_by_name(self, name):
            return mock_property
    
    engine = PropertyQuestionEngine(MockDBService(), None)
    
    for question in test_questions:
        print(f"Pregunta: '{question}'")
        question_type = engine._detect_question_type(question)
        print(f"  Tipo: {question_type}")
        answer = engine._generate_answer(question_type, mock_property)
        print(f"  Respuesta: {answer[:100]}...")
        print("-" * 80)
