"""
TavilyService Híbrido - Combina datos de web (Tavily) + Base de Datos
Siempre enriquece con precio, banco y agente desde la BD
"""

import json
import re
import logging
from urllib.parse import urlparse
from typing import Dict, Any, Optional

from tavily import TavilyClient
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from llama_index.core import Settings
from llama_index.core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

ALLOWED_DOMAIN = "bienesadjudicadoscr.com"
BASE_URL = "https://bienesadjudicadoscr.com/propiedades/"


# ============================================================================
# PROMPT MEJORADO - Incluye datos de BD
# ============================================================================

TAVILY_HYBRID_FORMAT_PROMPT = PromptTemplate("""
Eres EVA, un asistente experto en bienes raíces en Costa Rica. 

Te han proporcionado información de DOS fuentes sobre una propiedad:
1. Contenido extraído de la página web
2. Datos estructurados de nuestra base de datos

CONTENIDO DE LA PÁGINA WEB:
{web_content}

DATOS DE NUESTRA BASE DE DATOS:
{db_data}

URL DE LA PROPIEDAD: {url}

CONSULTA DEL USUARIO:
{user_query}

INSTRUCCIONES CRÍTICAS:
1. **Combina ambas fuentes de información** para dar la respuesta más completa
2. **Si hay conflicto de datos**, menciona ambas fuentes y recomienda verificar
3. **Datos de BD son más confiables** para:
   - Precio (siempre usar precio de BD si está disponible)
   - Banco/Entidad (SIEMPRE incluir del DB si existe)
   - Agente a cargo (SIEMPRE incluir del DB si existe)
   - Características técnicas (habitaciones, baños, área)

4. **Estructura de la respuesta:**
   - ## 🏠 [Nombre de la propiedad]
   - Resumen breve
   - ### 💰 Precio
   - ### 📍 Ubicación  
   - ### 🔑 Características Principales
   - ### 🏦 Información del Banco/Entidad (OBLIGATORIO si está en DB)
   - ### 👤 Agente a Cargo (OBLIGATORIO si está en DB)
   - ### 📞 Contacto

5. **Al final SIEMPRE incluye:**
   🔗 **Ver propiedad completa:** {url}

6. **Si faltan datos importantes:**
   - Indica qué información no está disponible
   - Sugiere contactar al agente directamente

7. **Tono:** Profesional, amigable, útil. Máximo 3-4 emojis.

RESPUESTA FORMATEADA:
""")


class TavilyBienesQueryEngine(BaseQueryEngine):
    """
    Query Engine híbrido que combina:
    - Datos de la página web (via Tavily crawl)
    - Datos estructurados de la base de datos

    Siempre proporciona precio, banco y agente desde la BD cuando estén disponibles.
    """

    # Palabras clave que indican contenido para publicación pública
    PUBLIC_CONTENT_KEYWORDS = [
        # Posts y publicaciones
        'post', 'publicación', 'publicar', 'publica', 'publicado',
        # Redes sociales específicas
        'instagram', 'facebook', 'twitter', 'tiktok', 'linkedin', 'youtube',
        'whatsapp', 'telegram', 'pinterest', 'snapchat',
        # Términos generales
        'redes sociales', 'red social', 'social media', 'rrss',
        'compartir en redes', 'compartir público', 'público',
        'subir', 'subida', 'subo', 'sube',  # subir a redes
        'timeline', 'feed', 'historia', 'historias', 'story',
        # Marketing y promoción
        'anuncio', 'anuncios', 'campaña', 'campaña de marketing',
        'promoción', 'promocionar', 'promociona', 'promocionable',
        'viral', 'viralizar', 'va a viral',
        # Usos generales de difusión pública
        'difund', 'divulgación', 'divulgar',
        'promocional', 'publicitario', 'publicidad',
        'para mostrar', 'mostrar en', 'para enseñar'
    ]

    def __init__(self, api_key: str, property_db_service):
        """
        Args:
            api_key: Tavily API key
            property_db_service: Instancia de PropertyDatabaseService
        """
        super().__init__(callback_manager=CallbackManager([]))
        self.api_key = api_key
        self.client = TavilyClient(api_key=api_key)
        self.property_db_service = property_db_service
        logger.info("✓ TavilyBienesQueryEngine inicializado (Web + BD)")

    def _is_public_content_request(self, query: str) -> bool:
        """
        Detecta si el usuario solicita contenido para publicación pública
        (post, redes sociales, anuncio, etc.)
        """
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.PUBLIC_CONTENT_KEYWORDS)

    def _ask_post_requirements(self, db_data: Dict[str, Any], url: str) -> Response:
        """
        Hace preguntas iniciales cuando el usuario solicita crear un post.
        Esto asegura que el post tenga la información que el usuario realmente quiere.
        """
        try:
            property_name = db_data.get('nombre', 'esta propiedad') if db_data else 'esta propiedad'

            questions_response = f"""
Perfecto, voy a crear un post atractivo para redes sociales sobre **{property_name}**.

Para que el post sea exactamente como lo quieres, déjame hacer unas preguntas:

1️⃣ **¿Qué aspecto quieres destacar principalmente?**
   - 🏠 Diseño y arquitectura
   - 📍 Ubicación y zona
   - 💰 Precio y oportunidad
   - 🌳 Amenidades y beneficios
   - ✨ Combinación de todo

2️⃣ **¿Qué tono prefieres?**
   - 📢 Profesional y formal
   - 😊 Amigable y casual
   - 🎯 Directo y agresivo

3️⃣ **¿Qué quieres que haga el interesado?**
   - 📞 Que te llame
   - 💬 Que mande mensaje
   - 🔗 Que visite el enlace
   - ❤️ Que le ponga like y comenta

4️⃣ **¿Qué agente quieres que aparezca en el post?**
   - 👤 Agente específico (dime el nombre)
   - ❌ Sin agente (solo información de la propiedad)
   - 📱 Tu contacto (teléfono/email)

Cuéntame estos detalles y crearé un post perfecto para ti! ✨
"""
            logger.info(f"📱 Preguntas de post generadas para: {property_name}")
            return Response(response=questions_response.strip())

        except Exception as e:
            logger.error(f"❌ Error generando preguntas de post: {e}")
            return Response(
                response="Claro, voy a crear un post atractivo. Por favor cuéntame:\n"
                         "- ¿Qué quieres que destaque? (diseño, ubicación, precio, amenidades)\n"
                         "- ¿Tono formal o casual?\n"
                         "- ¿Qué acción quieres (llamada, mensaje, visita)?\n"
                         "- ¿Qué agente quieres en el post? (nombre o sin agente)"
            )

    def _is_allowed_url(self, u: str) -> bool:
        """Verifica que la URL sea del dominio permitido."""
        host = urlparse(u).netloc.lower()
        return host == ALLOWED_DOMAIN or host.endswith("." + ALLOWED_DOMAIN)

    def _query(self, query_bundle: QueryBundle) -> Response:
        """
        Ejecuta búsqueda híbrida: Tavily (web) + BD.
        """
        query = query_bundle.query_str
        logger.info(f"\n{'='*60}")
        logger.info(f"🌐 TAVILY HYBRID SEARCH - {query}")
        logger.info(f"{'='*60}")

        # Detectar si es para contenido público
        is_public_content = self._is_public_content_request(query)
        if is_public_content:
            logger.info("📱 Modo: CONTENIDO PÚBLICO (omitiendo banco/agente)")
        else:
            logger.info("🔒 Modo: CONSULTA PRIVADA (incluye banco/agente)")

        # Extraer URLs del query
        urls = re.findall(r"https?://\S+", query)

        if urls:
            allowed = [u for u in urls if self._is_allowed_url(u)]
            if not allowed:
                logger.warning(f"⚠️ URLs no permitidas: {urls}")
                return Response(
                    response=(
                        "Solo puedo buscar dentro de **bienesadjudicadoscr.com**. "
                        "Por favor proporciona un enlace válido de ese sitio."
                    )
                )
            target_url = allowed[0]
            logger.info(f"🎯 URL objetivo: {target_url}")
        else:
            logger.warning(f"⚠️ No se detectó ninguna URL en la consulta")
            return Response(
                response=(
                    "Para buscar información en la web, necesito que me proporciones "
                    "el enlace (URL) específico de la propiedad en bienesadjudicadoscr.com"
                )
            )

        try:
            # ============================================================
            # PASO 1: OBTENER DATOS DE LA BASE DE DATOS
            # ============================================================
            logger.info(f"📊 Consultando base de datos...")
            db_data = self.property_db_service.get_property_by_url(target_url)

            if db_data:
                logger.info(f"✓ Datos de BD obtenidos: {db_data.get('nombre')}")
                # AQUÍ: Pasar is_public_content para omitir banco/agente si es público
                db_formatted = self.property_db_service.format_property_data_for_llm(
                    db_data,
                    for_public_content=is_public_content
                )
            else:
                logger.warning("⚠️ Propiedad no encontrada en BD")
                db_formatted = "No se encontraron datos en nuestra base de datos para esta URL."

            # ============================================================
            # PASO 2: CRAWL CON TAVILY (PÁGINA WEB)
            # ============================================================
            logger.info(f"📡 Crawleando página web con Tavily...")

            tavily_response = self.client.crawl(
                target_url,
                instructions=(
                    "Extrae toda la información relevante sobre la propiedad: "
                    "descripción, características, ubicación, amenidades, "
                    "condiciones de venta, y cualquier detalle adicional importante.\n\n"
                    f"Consulta del usuario: {query}"
                ),
            )

            logger.info(f"✓ Crawl completado")

            # Extraer contenido
            web_content = self._extract_content_from_tavily(tavily_response)

            if not web_content or len(web_content.strip()) < 50:
                logger.warning("⚠️ Contenido web muy corto o vacío")
                # Si no hay contenido web, usar solo datos de BD
                if db_data:
                    web_content = "La página web no proporcionó información detallada."
                else:
                    return Response(
                        response=(
                            f"No pude obtener información suficiente de {target_url}. "
                            "Por favor verifica el enlace o intenta más tarde."
                        )
                    )

            logger.info(f"✓ Contenido web extraído: {len(web_content)} caracteres")

            # ============================================================
            # PASO 3: SI ES POST, HACER PREGUNTAS PRIMERO
            # ============================================================
            if is_public_content:
                # Verificar si el usuario ya respondió a preguntas previas
                # Buscamos en el query si hay parámetros que indiquen detalles del post
                has_post_details = any(
                    keyword in query.lower()
                    for keyword in [
                        'tono', 'formal', 'casual', 'incluye', 'destaca', 'show',
                        'llamada a la acción', 'cta', 'que', 'quiero', 'quieres',
                        'ubicación', 'diseño', 'arquitectura', 'amenidades', 'precio',
                        'llame', 'llamen', 'mande', 'mensaje', 'visite', 'visita',
                        'destaca', 'muestra', 'highlights', 'professional', 'atractivo',
                        'amigable', 'serio', 'elegante', 'moderno', 'contemporáneo'
                    ]
                )

                if not has_post_details:
                    # Primera vez: hacer preguntas sobre qué incluir en el post
                    logger.info("📱 Modo POST: Haciendo preguntas iniciales sobre el contenido")
                    return self._ask_post_requirements(db_data, target_url)

            # ============================================================
            # PASO 4: COMBINAR Y FORMATEAR CON LLM
            # ============================================================
            formatted_content = self._format_hybrid_with_llm(
                web_content=web_content,
                db_data=db_formatted,
                url=target_url,
                user_query=query,
                is_public_content=is_public_content
            )

            return Response(response=formatted_content)

        except Exception as e:
            logger.error(f"❌ Error en búsqueda híbrida: {e}", exc_info=True)
            return Response(
                response=(
                    f"Ocurrió un error al buscar información:\n\n"
                    f"**Error:** {str(e)}\n\n"
                    f"Por favor intenta nuevamente o verifica el enlace."
                )
            )

    def _extract_content_from_tavily(self, tavily_response: Dict[str, Any]) -> str:
        """Extrae contenido útil de la respuesta de Tavily."""
        try:
            # Intentar diferentes estructuras
            if isinstance(tavily_response, dict) and 'content' in tavily_response:
                content = tavily_response['content']
                if isinstance(content, str):
                    return content
                elif isinstance(content, list) and content:
                    if isinstance(content[0], str):
                        return "\n\n".join(content)
                    elif isinstance(content[0], dict) and 'text' in content[0]:
                        return "\n\n".join(item['text'] for item in content if 'text' in item)
            
            # Si es string directo
            if isinstance(tavily_response, str):
                return tavily_response
            
            # Fallback a JSON
            logger.warning("⚠️ Estructura de Tavily no reconocida, usando JSON")
            return json.dumps(tavily_response, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo contenido: {e}")
            return str(tavily_response)

    def _format_hybrid_with_llm(
        self,
        web_content: str,
        db_data: str,
        url: str,
        user_query: str,
        is_public_content: bool = False
    ) -> str:
        """
        Formatea combinando datos web + BD usando el LLM.
        Adapta el prompt según si es para contenido público o privado.
        """
        try:
            llm = Settings.llm

            # Truncar contenido web si es muy largo
            max_content_length = 2500
            if len(web_content) > max_content_length:
                web_content = web_content[:max_content_length] + "\n\n[... contenido truncado ...]"

            # Seleccionar prompt según tipo de contenido
            if is_public_content:
                # Prompt para contenido público (sin banco/agente a menos que usuario lo pida)
                prompt_template = PromptTemplate("""
Eres EVA, un asistente experto en bienes raíces en Costa Rica, especializado en crear posts atractivos para redes sociales.

Te han proporcionado información de DOS fuentes sobre una propiedad:
1. Contenido extraído de la página web
2. Datos estructurados de nuestra base de datos

CONTENIDO DE LA PÁGINA WEB:
{web_content}

DATOS DE NUESTRA BASE DE DATOS:
{db_data}

URL DE LA PROPIEDAD: {url}

CONSULTA DEL USUARIO:
{user_query}

INSTRUCCIONES CRÍTICAS PARA POSTS EN REDES SOCIALES:

1. **INFORMACIÓN PROHIBIDA - NUNCA incluyas automáticamente**:
   - Banco o entidad financiera
   - Nombres de agentes internos (a menos que el usuario lo pida)
   - Contactos internos

2. **AGENTE EN EL POST**:
   - Si el usuario menciona "sin agente" → NO incluyas agente
   - Si el usuario menciona "agente: [nombre]" → Usa SOLO ese nombre y contacto
   - Si el usuario menciona "mi contacto" → Usa los datos que proporcione
   - Si NO menciona nada sobre agente → NO incluyas agente

3. **COMBINA ambas fuentes** para información completa: web + datos de BD

4. **IDENTIFICA** qué aspecto quiere destacar el usuario:
   - Si menciona "ubicación", destaca zona, transporte, seguridad
   - Si menciona "diseño", destaca arquitectura, amenidades, modernidad
   - Si menciona "precio", enfóquete en la oportunidad y valor
   - Si menciona "llamada a la acción", incluye CTA clara

5. **TONO según usuario**:
   - "formal/profesional" → Lenguaje corporativo, elegante
   - "casual/amigable" → Conversacional, emojis, cercano

6. **ESTRUCTURA DEL POST**:
   - Línea de enganche (máximo 1-2 emojis)
   - Descripción principal (2-3 párrafos máximo)
   - Características clave en bullets
   - Agente (SOLO si el usuario lo pidió)
   - Llamada a la acción clara
   - hashtags relevantes (máximo 5)

7. **RESTRICCIONES**: NUNCA incluyas banco, entidad, agentes no solicitados

8. **Longitud optimal**: 200-300 caracteres de párrafo principal (Instagram/Facebook friendly)

RESPUESTA - Crea el post ahora:
""")
            else:
                # Prompt para consultas privadas/internas (con banco/agente)
                prompt_template = PromptTemplate("""
Eres EVA, un asistente experto en bienes raíces en Costa Rica.

Te han proporcionado información de DOS fuentes sobre una propiedad:
1. Contenido extraído de la página web
2. Datos estructurados de nuestra base de datos

CONTENIDO DE LA PÁGINA WEB:
{web_content}

DATOS DE NUESTRA BASE DE DATOS:
{db_data}

URL DE LA PROPIEDAD: {url}

CONSULTA DEL USUARIO:
{user_query}

INSTRUCCIONES CRÍTICAS:
1. **Combina ambas fuentes de información** para dar la respuesta más completa
2. **Si hay conflicto de datos**, menciona ambas fuentes y recomienda verificar
3. **Datos de BD son más confiables** para:
   - Precio (siempre usar precio de BD si está disponible)
   - Banco/Entidad (SIEMPRE incluir del DB si existe)
   - Agente a cargo (SIEMPRE incluir del DB si existe)
   - Características técnicas (habitaciones, baños, área)

4. **Estructura de la respuesta:**
   - ## 🏠 [Nombre de la propiedad]
   - Resumen breve
   - ### 💰 Precio
   - ### 📍 Ubicación
   - ### 🔑 Características Principales
   - ### 🏦 Información del Banco/Entidad (OBLIGATORIO si está en DB)
   - ### 👤 Agente a Cargo (OBLIGATORIO si está en DB)
   - ### 📞 Contacto

5. **Al final SIEMPRE incluye:**
   🔗 **Ver propiedad completa:** {url}

6. **Si faltan datos importantes:**
   - Indica qué información no está disponible
   - Sugiere contactar al agente directamente

7. **Tono:** Profesional, amigable, útil. Máximo 3-4 emojis.

RESPUESTA FORMATEADA:
""")

            # Formatear prompt
            prompt = prompt_template.format(
                web_content=web_content,
                db_data=db_data,
                url=url,
                user_query=user_query
            )

            logger.info("🤖 Enviando a LLM para formateo híbrido...")

            # Generar respuesta
            formatted_response = llm.complete(prompt).text

            logger.info("✓ Respuesta híbrida generada")

            return formatted_response.strip()

        except Exception as e:
            logger.error(f"❌ Error formateando con LLM: {e}", exc_info=True)

            # Fallback manual
            return self._fallback_hybrid_format(web_content, db_data, url, is_public_content)

    def _fallback_hybrid_format(
        self,
        web_content: str,
        db_data: str,
        url: str,
        is_public_content: bool = False
    ) -> str:
        """Formato híbrido básico si el LLM falla."""
        logger.warning("⚠️ Usando formato híbrido fallback (sin LLM)")

        content_type = "PÚBLICA" if is_public_content else "PRIVADA"
        return f"""## 🏠 Información de la Propiedad [{content_type}]

### Datos de Nuestra Base de Datos:
{db_data}

### Información de la Página Web:
{web_content[:1000]}...

---

🔗 **Ver propiedad completa:** {url}

_Información combinada de nuestra base de datos y la página web oficial_
"""

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        """Versión async."""
        return self._query(query_bundle)

    def _get_prompt_modules(self):
        """Requerido por BaseQueryEngine."""
        return {}