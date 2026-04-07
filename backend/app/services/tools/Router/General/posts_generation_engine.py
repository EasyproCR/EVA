"""
Posts Generation Engine - Genera contenido de posts para redes sociales
Accesible para todos los usuarios sin restricción de roles
"""

import logging
import re
from typing import Optional, Dict
from difflib import SequenceMatcher
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from llama_index.core import Settings
from sqlalchemy import text

logger = logging.getLogger(__name__)


class PostsGenerationEngine(BaseQueryEngine):
    """
    Query Engine para generar/elaborar posts para redes sociales.

    Si suministra ID o URL de propiedad, obtiene datos reales y genera post específico.
    Si no, genera post genérico basado en descripción.

    Acceso: ABIERTO para todos los usuarios
    Funcionalidad: Crear/generar contenido de posts optimizado por plataforma
    """

    # Keywords para detectar solicitudes de generación/elaboración de posts
    GENERATION_KEYWORDS = {
        'elabora', 'elaborar', 'genera', 'generar', 'crea', 'crear', 'escribe',
        'escribir', 'haz', 'hacer', 'redacta', 'redactar', 'compón', 'componer',
        'realiza', 'realizar', 'plantea', 'plantear', 'sugiere', 'sugerir',
        'post', 'posts', 'publicación', 'publicaciones', 'contenido',
        'caption', 'copy', 'texto', 'idea'
    }

    # Keywords para plataformas específicas
    PLATFORM_KEYWORDS = {
        'instagram': {'instagram', 'ig', 'reels', 'reel', 'stories', 'story'},
        'facebook': {'facebook', 'fb'},
        'twitter': {'twitter', 'x', 'tweet'},
        'tiktok': {'tiktok', 'tt'},
        'linkedin': {'linkedin', 'profesional'},
        'youtube': {'youtube', 'yt'},
        'general': {'general', 'social', 'red social', 'redes sociales'}
    }

    # Tipos de contenido
    CONTENT_TYPES = {
        'promocional': {'promoción', 'promocional', 'venta', 'oferta', 'descuento', 'promo'},
        'informativo': {'información', 'informativo', 'noticia', 'update', 'actualización'},
        'entretenimiento': {'divertido', 'humor', 'joke', 'chistoso', 'random', 'entretenimiento'},
        'educativo': {'educativo', 'tutorial', 'tips', 'consejo', 'guía', 'cómo'},
        'inspirador': {'inspirador', 'motivación', 'inspirar', 'motivador'}
    }

    def __init__(self, sql_database=None):
        """Inicializar el engine de generación de posts"""
        super().__init__(callback_manager=CallbackManager([]))
        self.sql_database = sql_database
        self.user_roles = []  # Se asigna desde el router (acceso abierto)
        logger.info("✓ PostsGenerationEngine inicializado")

    def _is_generation_request(self, query: str) -> bool:
        """
        Detecta si la pregunta pide generar/elaborar un post
        ULTRA FLEXIBLE: tolera faltas ortográficas desde 50%
        """
        query_lower = query.lower()
        words = query_lower.split()

        best_score = 0.0
        for word in words:
            for keyword in self.GENERATION_KEYWORDS:
                # Similitud exacta (rápido)
                if keyword in word or word in keyword:
                    return True

                # Similitud difusa desde 50%
                similarity = SequenceMatcher(None, word, keyword).ratio()
                if similarity >= 0.50:
                    best_score = similarity
                    logger.info(f"  ◇ Fuzzy generation keyword ({best_score*100:.0f}%): '{word}' ≈ '{keyword}'")
                    return True

        return False

    def _extract_property_id(self, query: str) -> Optional[int]:
        """Extrae ID de propiedad de la query (ej: 'id 150' o '#150')"""
        # Buscar patrones: "id 123", "#123", "propiedad 123", "property 123"
        patterns = [
            r'(?:id|propiedad|property)\s+#?(\d+)',  # "id 150" o "propiedad 150"
            r'#(\d+)',  # "#150"
            r'(?:del|del\s+)?(?:inmueble|propiedad)\s+(\d+)',  # "del inmueble 150"
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return int(match.group(1))

        return None

    def _extract_property_url(self, query: str) -> Optional[str]:
        """Extrae URL de propiedad de la query"""
        # Buscar URLs de bienesadjudicados.com o URLs genéricas
        url_pattern = r'https?://[^\s\)]+'
        match = re.search(url_pattern, query)
        if match:
            return match.group(0)
        return None

    def _get_property_data(self, property_id: int) -> Optional[Dict]:
        """Obtiene datos de la propiedad desde BD"""
        if not self.sql_database:
            logger.warning("SQL Database no disponible para obtener datos de propiedad")
            return None

        try:
            connection = self.sql_database._engine.connect()

            sql = """
            SELECT
                id, name, description, price, location,
                property_type, bedrooms, bathrooms,
                area, agent_name, bank_name, status
            FROM properties
            WHERE id = :property_id
            LIMIT 1
            """

            result = connection.execute(text(sql), {'property_id': property_id})
            row = result.fetchone()
            connection.close()

            if row:
                return dict(row._mapping)
            return None

        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de propiedad: {str(e)}")
            return None

    def _detect_platform(self, query: str) -> str:
        """
        Detecta la plataforma objetivo del post
        ULTRA FLEXIBLE: tolera faltas ortográficas desde 50%
        """
        query_lower = query.lower()
        words = query_lower.split()

        best_platform = "instagram"  # Default
        best_score = 0.0

        for platform, keywords in self.PLATFORM_KEYWORDS.items():
            for word in words:
                for keyword in keywords:
                    # Similitud exacta (rápido)
                    if keyword in word or word in keyword:
                        logger.info(f"  ✓ Plataforma detectada: {platform}")
                        return platform

                    # Similitud difusa desde 50%
                    similarity = SequenceMatcher(None, word, keyword).ratio()
                    if similarity >= 0.50 and similarity > best_score:
                        best_score = similarity
                        best_platform = platform
                        logger.info(f"  ◇ Fuzzy platform ({best_score*100:.0f}%): '{word}' ≈ '{keyword}' → {platform}")

        return best_platform

    def _detect_content_type(self, query: str) -> str:
        """
        Detecta el tipo de contenido que se solicita
        ULTRA FLEXIBLE: tolera faltas ortográficas desde 50%
        """
        query_lower = query.lower()
        words = query_lower.split()

        best_content_type = "promocional"  # Default
        best_score = 0.0

        for content_type, keywords in self.CONTENT_TYPES.items():
            for word in words:
                for keyword in keywords:
                    # Similitud exacta (rápido)
                    if keyword in word or word in keyword:
                        logger.info(f"  ✓ Tipo contenido detectado: {content_type}")
                        return content_type

                    # Similitud difusa desde 50%
                    similarity = SequenceMatcher(None, word, keyword).ratio()
                    if similarity >= 0.50 and similarity > best_score:
                        best_score = similarity
                        best_content_type = content_type
                        logger.info(f"  ◇ Fuzzy content ({best_score*100:.0f}%): '{word}' ≈ '{keyword}' → {content_type}")

        return best_content_type

    def _query(self, query_bundle: QueryBundle) -> Response:
        """
        Procesa solicitudes de generación de posts.
        Si hay ID/URL de propiedad, obtiene datos y genera post específico.
        Si la solicitud es vaga, hace preguntas aclaratorias.
        """
        query = query_bundle.query_str
        logger.info(f"📝 Posts Generation Request: {query}")

        # Verificar si es una solicitud de generación
        if not self._is_generation_request(query):
            logger.info(f"  ℹ️ No es solicitud de generación, delegando a otro engine")
            return Response(response="")  # Retorna vacío para que otro engine lo procese

        logger.info(f"  🎨 Detectada solicitud de generación de posts")

        try:
            # Detectar plataforma y tipo de contenido
            platform = self._detect_platform(query)
            content_type = self._detect_content_type(query)

            # Verificar si la solicitud es muy vaga
            query_lower = query.lower()
            is_vague = len(query) < 20  # Muy corta
            has_no_specifics = not any(word in query_lower for word in ['propiedad', 'id', 'http', 'precio', 'ubicación', 'para'])

            if is_vague and has_no_specifics:
                # Hacer preguntas aclaratorias
                clarification = (
                    "🤔 **Necesito más información para generar un post mejor:**\n\n"
                    "1️⃣ **¿De qué es el post?** (ej: una propiedad específica, promoción general, etc)\n"
                    "2️⃣ **¿Para cuál plataforma?** (Instagram, Facebook, TikTok, LinkedIn, Twitter, etc)\n"
                    "3️⃣ **¿Qué tipo de contenido?** (promocional, informativo, educativo, inspirador)\n"
                    "4️⃣ **¿Algún detalle importante?** (precio, ubicación, características especiales)\n\n"
                    "💡 **Ejemplo:** 'Genera un post para Instagram de una propiedad de 3 habitaciones en San José, precio $150,000'\n\n"
                    "¿En qué más te puedo ayudar con tus publicaciones? 😊"
                )
                return Response(response=clarification)

            # Detectar si hay ID o URL de propiedad
            property_id = self._extract_property_id(query)
            property_url = self._extract_property_url(query)
            property_data = None

            if property_id:
                logger.info(f"  🏠 ID de propiedad detectado: {property_id}")
                property_data = self._get_property_data(property_id)
                if property_data:
                    logger.info(f"  ✅ Datos de propiedad obtenidos")
                else:
                    logger.warning(f"  ⚠️ No se encontraron datos para propiedad ID {property_id}")
            elif property_url:
                logger.info(f"  🔗 URL detectada: {property_url}")

            logger.info(f"  📱 Plataforma: {platform} | 📊 Tipo: {content_type}")

            response_text = self._generate_post(query, platform, content_type, property_data, property_url)
            logger.info(f"  ✅ Post generado exitosamente")

            # Agregar pregunta de ayuda adicional al final
            response_with_help = (
                f"{response_text}\n\n"
                f"---\n"
                f"¿Te puedo ayudar con algo más? (editar, cambiar tono, otra plataforma, etc) 💬"
            )

            return Response(response=response_with_help)

        except Exception as e:
            logger.error(f"  ❌ Error generando post: {str(e)}", exc_info=True)
            return Response(response=f"⚠️ Error al generar el post: {str(e)}")

    def _generate_post(self, query: str, platform: str, content_type: str,
                       property_data: Optional[Dict] = None, property_url: Optional[str] = None) -> str:
        """
        Genera contenido de post usando el LLM
        Si hay datos de propiedad, los incluye en el prompt
        """
        try:
            llm = Settings.llm

            # Construir prompt específico por plataforma
            platform_guidelines = self._get_platform_guidelines(platform)
            content_type_guidance = self._get_content_type_guidance(content_type)

            # Agregar contexto de propiedad si está disponible
            property_context = ""
            if property_data:
                property_context = self._format_property_context(property_data)

            prompt = (
                f"Eres un experto en marketing inmobiliario y redes sociales.\n\n"
                f"El usuario solicita:\n{query}\n\n"
            )

            if property_context:
                prompt += f"DATOS DE LA PROPIEDAD:\n{property_context}\n\n"

            if property_url:
                prompt += f"URL de la propiedad: {property_url}\n\n"

            prompt += (
                f"Por favor genera un post con estas características:\n\n"
                f"{platform_guidelines}\n\n"
                f"{content_type_guidance}\n\n"
                f"PAUTAS:\n"
                f"- Usa emojis relevantes cuando sea apropiado\n"
                f"- Mantén un tono natural y atrayente\n"
                f"- Incluye un CTA (llamado a la acción) si es necesario\n"
                f"- Sé conciso pero impactante\n"
                f"- Optimiza para el objetivo del post\n"
                f"- Flexible en la interpretación - crea contenido que tenga sentido\n\n"
                f"Respuesta:"
            )

            response_text = llm.complete(prompt).text

            # Formatear respuesta con contexto
            platform_emoji = self._get_platform_emoji(platform)
            formatted_response = (
                f"{platform_emoji} **NUEVO POST GENERADO PARA {platform.upper()}**\n\n"
                f"{response_text}"
            )

            return formatted_response

        except Exception as e:
            logger.error(f"❌ Error en _generate_post: {str(e)}")
            raise

    def _format_property_context(self, property_data: Dict) -> str:
        """Formatea los datos de la propiedad para incluir en el prompt"""
        context = ""

        if property_data.get('name'):
            context += f"📍 **{property_data['name']}**\n"

        if property_data.get('price'):
            context += f"💰 Precio: ₡{property_data['price']:,}\n"

        if property_data.get('location'):
            context += f"📌 Ubicación: {property_data['location']}\n"

        if property_data.get('property_type'):
            context += f"🏠 Tipo: {property_data['property_type']}\n"

        if property_data.get('bedrooms'):
            context += f"🛏️ Habitaciones: {property_data['bedrooms']}\n"

        if property_data.get('bathrooms'):
            context += f"🚿 Baños: {property_data['bathrooms']}\n"

        if property_data.get('area'):
            context += f"📐 Área: {property_data['area']} m²\n"

        if property_data.get('description'):
            context += f"📝 Descripción: {property_data['description']}\n"

        if property_data.get('bank_name'):
            context += f"🏦 Entidad: {property_data['bank_name']}\n"

        return context

    def _get_platform_guidelines(self, platform: str) -> str:
        """Retorna guías específicas por plataforma"""
        guidelines = {
            'instagram': (
                "**PLATAFORMA: Instagram**\n"
                "- Máximo 2200 caracteres en caption\n"
                "- 3-5 hashtags relevantes (#PropiedadesCostaRica #Remate #BancariasAfiliadas etc)\n"
                "- Emojis para aumentar engagement\n"
                "- Menciona ubicación con precisión\n"
                "- Ideal para fotos de propiedades, amenidades\n"
                "- CTA: 'DM para más info', 'Link en bio', 'Visita ahora'"
            ),
            'facebook': (
                "**PLATAFORMA: Facebook**\n"
                "- Tono conversacional y cercano\n"
                "- Puede ser más largo (hasta 5000 caracteres)\n"
                "- Incluye preguntas: '¿Te interesa esta propiedad?'\n"
                "- Buen para descripciones detalladas\n"
                "- 1-2 hashtags máximo\n"
                "- Emojis caseros"
            ),
            'twitter': (
                "**PLATAFORMA: Twitter/X**\n"
                "- Máximo 280 caracteres - SER MUY CONCISO\n"
                "- Directo: Precio, ubicación, destaque principal\n"
                "- Ideal para noticias de subastas, descuentos\n"
                "- 1-2 hashtags\n"
                "- Link shortener para URL"
            ),
            'tiktok': (
                "**PLATAFORMA: TikTok**\n"
                "- Caption corto pero provocador\n"
                "- Hook en primeros 3 segundos (video tour)\n"
                "- 'No lo vas a creer' o sensacionalismo positivo\n"
                "- Hashtags de tendencia\n"
                "- CTA: 'Clic en bio'"
            ),
            'linkedin': (
                "**PLATAFORMA: LinkedIn**\n"
                "- Tono profesional e inmobiliario\n"
                "- Enfoque en oportunidad de inversión\n"
                "- Storytelling: 'Cómo esta propiedad...\n"
                "- Máximo 1300 caracteres\n"
                "- Hashtags profesionales"
            ),
            'youtube': (
                "**PLATAFORMA: YouTube**\n"
                "- Para videos de tour de propiedad\n"
                "- Título: 'PROPIEDAD EN [UBICACIÓN] - [PRECIO]'\n"
                "- Descripción: Detalles completos + link\n"
                "- CTA clara: 'Contacta aquí' + número/email"
            ),
            'general': (
                "**PLATAFORMA: Redes Sociales Generales**\n"
                "- Contenido versátil para múltiples plataformas\n"
                "- Destaca: ubicación, precio, tipo de propiedad\n"
                "- Tono profesional pero accesible\n"
                "- Emojis moderados pero efectivos"
            )
        }
        return guidelines.get(platform, guidelines['general'])

    def _get_content_type_guidance(self, content_type: str) -> str:
        """Retorna guías específicas por tipo de contenido"""
        guidance = {
            'promocional': (
                "**TIPO: Contenido Promocional (VENTA)**\n"
                "- Destaca precio competitivo y oportunidad\n"
                "- Urgencia: 'Oferta limitada', 'En subasta hasta...'\n"
                "- CTA fuerte: 'Agendar cita', 'Ver ahora', 'Información'\n"
                "- Características principales: ubicación, precio, tipo"
            ),
            'informativo': (
                "**TIPO: Contenido Informativo**\n"
                "- Presenta datos claros: precio, área, tipo\n"
                "- Ubicación precisa y referencias\n"
                "- Características y amenidades\n"
                "- Facilita la búsqueda (filtrable)"
            ),
            'entretenimiento': (
                "**TIPO: Contenido de Entretenimiento**\n"
                "- 'Homes that wow', 'Increíble transformación'\n"
                "- Noticias de mercado inmobiliario\n"
                "- Curiosidades sobre la propiedad\n"
                "- Antes/después si es remodelación"
            ),
            'educativo': (
                "**TIPO: Contenido Educativo**\n"
                "- Tips: 'Cómo elegir propiedad en remate'\n"
                "- Guía: 'Proceso de subasta bancaria'\n"
                "- Info sobre ubicación\n"
                "- Establece expertise en mercado inmobiliario"
            ),
            'inspirador': (
                "**TIPO: Contenido Inspirador**\n"
                "- 'Tu casa de sueños a precio justo'\n"
                "- Historias de éxito (clientes)\n"
                "- Oportunidades de vida better\n"
                "- Confianza en el proceso"
            )
        }
        return guidance.get(content_type, "Contenido promocional de propiedad")

    def _get_platform_emoji(self, platform: str) -> str:
        """Retorna emoji para plataforma"""
        emoji_map = {
            'instagram': '📸',
            'facebook': '👍',
            'twitter': '🐦',
            'tiktok': '🎵',
            'linkedin': '💼',
            'youtube': '📹',
            'general': '📱'
        }
        return emoji_map.get(platform, '📱')

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        """Versión async de _query."""
        return self._query(query_bundle)

    def set_user_roles(self, roles):
        """Setter para asignar roles del usuario desde el router (no afecta acceso abierto)"""
        self.user_roles = roles if roles else []
        logger.info(f"  👤 Roles asignados (acceso abierto para generación): {self.user_roles}")

    def _get_prompt_modules(self):
        """Requerido por BaseQueryEngine."""
        return {}
