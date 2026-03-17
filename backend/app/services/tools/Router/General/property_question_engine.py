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

        # Obtener datos de la propiedad
        property_data = None

        # 1️⃣ Intentar extraer ID (primero, más específico)
        property_id = self._extract_property_id(query)
        if property_id is not None:
            logger.info(f"  🆔 ID extraído: {property_id}")
            property_data = self.property_db_service.get_property_by_id(property_id)

        # 2️⃣ Si no encontró por ID, intentar extraer URL del query
        if not property_data:
            urls = re.findall(r'https?://\S+', query)
            if urls:
                # Si hay URL en el query, buscar por URL
                property_data = self.property_db_service.get_property_by_url(urls[0])

        # 3️⃣ Si no encontró por URL, buscar por nombre en el query
        if not property_data:
            # Extraer posible nombre de propiedad
            name_match = re.search(r'(?:de|del|sobre)\s+["\']?([^"\'?]+)["\']?', query, re.IGNORECASE)
            if name_match:
                property_name = name_match.group(1).strip()
                property_data = self.property_db_service.get_property_by_name(property_name)

        # 4️⃣ Si no encontró, intentar usar contexto (última propiedad de la conversación)
        if not property_data and self.context_manager:
            logger.info(f"  📚 Intentando obtener propiedad del contexto...")
            property_data = self.context_manager.get_last_property()
            if property_data:
                logger.info(f"  ✓ Propiedad obtenida del contexto: {property_data.get('nombre', 'N/A')}")

        if not property_data:
            return Response(
                response=(
                    "No encontré información de esa propiedad en nuestra base de datos. "
                    "¿Podrías proporcionar el enlace de la propiedad, su ID o más detalles?"
                )
            )

        # Detectar tipo de pregunta específica
        question_type = self._detect_question_type(query)

        # Si no hay tipo específico, mostrar resumen general
        if not question_type:
            return self._generate_property_summary(property_data)

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
        if re.search(r'\b(banco|entidad|institution|financiera|que banco)\b', query_lower):
            return 'banco'

        # Agente
        if re.search(r'\b(agente|asesor|encargado|contacto|representante|quien|esta a cargo)\b', query_lower):
            return 'agente'

        # Precio
        if re.search(r'\b(precio|costo|cuanto\s+cuesta|valor|cuanto\s+es|cual\s+es\s+el\s+precio)\b', query_lower):
            return 'precio'

        # Habitaciones
        if re.search(r'\b(habitacion|cuarto|dormitorio|bedroom|cuantas?\s+habitaciones|cuantos?\s+cuartos)\b', query_lower):
            return 'habitaciones'

        # Baños
        if re.search(r'\b(baño|bathroom|cuantos?\s+banos|cuantos?\s+sanitarios)\b', query_lower):
            return 'banos'

        # Ubicación
        if re.search(r'\b(ubicacion|ubicada|direccion|donde|queda|esta|donde\s+esta)\b', query_lower):
            return 'ubicacion'

        # Área/Tamaño
        if re.search(r'\b(area|tamaño|tamano|metros|m2|m²|cuanto\s+mide|tamaño\s+del\s+lote)\b', query_lower):
            return 'area'

        # Tipo
        if re.search(r'\b(tipo|categoria|clase|que\s+es|es\s+un|cual\s+es\s+el\s+tipo)\b', query_lower):
            return 'tipo'

        return None

    def _extract_property_id(self, query: str) -> Optional[int]:
        """
        Extrae ID de propiedad del query del usuario.

        Detecta patrones como:
        - "ID: 123" o "id: 123"
        - "ID 123"
        - "#ID 123"
        - "propiedad 123" (cuando es número único)

        Returns:
            int: ID de la propiedad o None
        """
        query_lower = query.lower()

        # Patrón 1: "ID: 123" o "id: 123"
        match = re.search(r'\bid\s*[:=]?\s*(\d+)\b', query_lower)
        if match:
            property_id = int(match.group(1))
            logger.info(f"  ✓ Patrón detectado: ID:{property_id}")
            return property_id

        # Patrón 2: "propiedad 123" (explícito)
        match = re.search(r'\bpropiedad\s+(\d+)\b', query_lower)
        if match:
            property_id = int(match.group(1))
            logger.info(f"  ✓ Patrón detectado: propiedad {property_id}")
            return property_id

        # Patrón 3: "#ID 123"
        match = re.search(r'#\s*id\s+(\d+)\b', query_lower)
        if match:
            property_id = int(match.group(1))
            logger.info(f"  ✓ Patrón detectado: #ID {property_id}")
            return property_id

        return None

    def _generate_property_summary(
        self,
        property_data: Dict[str, Any]
    ) -> Response:
        """
        Genera un resumen general cuando el usuario pregunta "dime información"
        sin especificar qué información exacta necesita.
        """
        prop_name = property_data.get('nombre', 'La propiedad')
        lines = [f"**{prop_name}**\n"]

        # Tipo de propiedad
        if property_data.get('tipo_propiedad'):
            lines.append(f"Tipo: **{property_data['tipo_propiedad']}**")

        # Ubicación
        ubicacion_parts = []
        if property_data.get('distrito'):
            ubicacion_parts.append(property_data['distrito'])
        if property_data.get('canton'):
            ubicacion_parts.append(property_data['canton'])
        if property_data.get('provincia'):
            ubicacion_parts.append(property_data['provincia'])
        if ubicacion_parts:
            lines.append(f"Ubicacion: **{', '.join(ubicacion_parts)}**")

        # Precio
        if property_data.get('precio_usd'):
            lines.append(f"Precio: **USD {float(property_data['precio_usd']):,.0f}**")
        elif property_data.get('precio_local'):
            lines.append(f"Precio local: **{float(property_data['precio_local']):,.0f}**")

        # Características
        if property_data.get('bedrooms'):
            lines.append(f"Habitaciones: **{property_data['bedrooms']}**")
        if property_data.get('bathrooms'):
            lines.append(f"Banos: **{property_data['bathrooms']}**")

        # Áreas
        if property_data.get('area_construccion'):
            lines.append(f"Area construccion: **{property_data['area_construccion']} m²**")
        if property_data.get('tamanio_lote'):
            lines.append(f"Tamanio del lote: **{property_data['tamanio_lote']} m²**")

        # Banco y Agente
        if property_data.get('nombre_banco'):
            lines.append(f"\nBanco/Entidad: **{property_data['nombre_banco']}**")
        if property_data.get('agent_name'):
            agente_info = f"Agente: **{property_data['agent_name']}**"
            if property_data.get('agent_phone_number'):
                agente_info += f" | Tel: {property_data['agent_phone_number']}"
            lines.append(agente_info)

        return Response(response="\n".join(lines))

    def _generate_answer(
        self,
        question_type: str,
        property_data: Dict[str, Any]
    ) -> str:
        """
        Genera respuesta ESPECIFICA según el tipo de pregunta.
        Solo devuelve lo solicitado, sin información extra.
        """
        prop_name = property_data.get('nombre', 'La propiedad')

        if question_type == 'banco':
            banco = property_data.get('nombre_banco')
            if banco:
                return f"**{prop_name}** pertenece a **{banco}**."
            else:
                return f"No hay información del banco para **{prop_name}**."

        elif question_type == 'agente':
            agent_name = property_data.get('agent_name')
            agent_phone = property_data.get('agent_phone_number')

            if agent_name:
                response = f"El agente es **{agent_name}**"
                if agent_phone:
                    response += f" | Tel: {agent_phone}"
                return response
            else:
                return "No hay información del agente disponible."

        elif question_type == 'precio':
            precio = property_data.get('precio_usd')
            if precio:
                return f"**USD {float(precio):,.0f}**"
            else:
                return "La información del precio no está disponible."

        elif question_type == 'habitaciones':
            bedrooms = property_data.get('bedrooms')
            if bedrooms:
                return f"**{bedrooms} habitaciones**"
            else:
                return "No hay información sobre habitaciones."

        elif question_type == 'banos':
            bathrooms = property_data.get('bathrooms')
            if bathrooms:
                return f"**{bathrooms} baños**"
            else:
                return "No hay información sobre baños."

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
                return f"**{ubicacion}**"
            else:
                return "No hay información de ubicación disponible."

        elif question_type == 'area':
            area_const = property_data.get('area_construccion')
            area_lote = property_data.get('tamanio_lote')

            parts = []
            if area_const:
                parts.append(f"Área construcción: **{area_const} m²**")
            if area_lote:
                parts.append(f"Tamaño lote: **{area_lote} m²**")

            if parts:
                return " | ".join(parts)
            else:
                return "No hay información sobre áreas disponible."

        elif question_type == 'tipo':
            tipo = property_data.get('tipo_propiedad')
            if tipo:
                return f"**{tipo}**"
            else:
                return "No hay información sobre el tipo de propiedad."

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
