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
                db_formatted = self.property_db_service.format_property_data_for_llm(db_data)
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
            # PASO 3: COMBINAR Y FORMATEAR CON LLM
            # ============================================================
            formatted_content = self._format_hybrid_with_llm(
                web_content=web_content,
                db_data=db_formatted,
                url=target_url,
                user_query=query
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
        user_query: str
    ) -> str:
        """
        Formatea combinando datos web + BD usando el LLM.
        """
        try:
            llm = Settings.llm
            
            # Truncar contenido web si es muy largo
            max_content_length = 2500
            if len(web_content) > max_content_length:
                web_content = web_content[:max_content_length] + "\n\n[... contenido truncado ...]"
            
            # Formatear prompt
            prompt = TAVILY_HYBRID_FORMAT_PROMPT.format(
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
            return self._fallback_hybrid_format(web_content, db_data, url)

    def _fallback_hybrid_format(
        self,
        web_content: str,
        db_data: str,
        url: str
    ) -> str:
        """Formato híbrido básico si el LLM falla."""
        logger.warning("⚠️ Usando formato híbrido fallback (sin LLM)")
        
        return f"""## 🏠 Información de la Propiedad

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