import logging
from typing import Dict, Any

from tavily import TavilyClient
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from llama_index.core import Settings
from llama_index.core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

INTERNET_SEARCH_PROMPT = PromptTemplate("""
Eres EVA, un asistente de IA profesional.

El usuario hizo una consulta que requirió buscar información en internet.
A continuación te presento los resultados obtenidos de la búsqueda web.

CONSULTA DEL USUARIO:
{user_query}

RESULTADOS DE LA BÚSQUEDA WEB:
{search_results}

INSTRUCCIONES:
1. Resume y sintetiza la información encontrada de forma clara y útil.
2. Responde directamente a lo que el usuario preguntó.
3. Si los resultados contienen información contradictoria, menciona ambas versiones.
4. Usa formato Markdown cuando ayude a la claridad (listas, negrita).
5. Si la información puede estar desactualizada, indícalo.
6. Máximo un emoji por respuesta.
7. Responde SIEMPRE en español.
8. Al final, si es relevante, menciona la fuente (nombre del sitio, no la URL completa).

RESPUESTA:
""")


class InternetSearchEngine(BaseQueryEngine):
    def __init__(self, api_key: str):
        super().__init__(callback_manager=CallbackManager([]))
        self.client = TavilyClient(api_key=api_key)
        logger.info("✓ InternetSearchEngine inicializado (búsqueda general)")

    def _query(self, query_bundle: QueryBundle) -> Response:
        query = query_bundle.query_str
        logger.info(f"🌐 BÚSQUEDA GENERAL EN INTERNET: {query}")

        try:
            search_response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                include_answer=True,
                include_raw_content=False,
            )

            search_text = self._format_results(search_response)

            if not search_text:
                return Response(
                    response="No encontré información suficiente en internet para responder tu consulta. "
                             "¿Podrías reformular la pregunta o darme más contexto?"
                )

            llm = Settings.llm
            prompt = INTERNET_SEARCH_PROMPT.format(
                user_query=query,
                search_results=search_text
            )

            final_response = llm.complete(prompt).text.strip()
            return Response(response=final_response)

        except Exception as e:
            logger.error(f"❌ Error en búsqueda general: {e}", exc_info=True)
            return Response(
                response=f"Ocurrió un error al buscar en internet: {str(e)}. "
                         "Por favor intenta de nuevo."
            )

    def _format_results(self, search_response: Dict[str, Any]) -> str:
        parts = []
        answer = search_response.get("answer", "")
        if answer:
            parts.append(f"RESUMEN RÁPIDO:\n{answer}\n")

        results = search_response.get("results", [])
        if results:
            parts.append("FUENTES ENCONTRADAS:")
            for i, r in enumerate(results, 1):
                title = r.get("title", "Sin título")
                content = r.get("content", "")
                url = r.get("url", "")
                if content:
                    content_preview = content[:600] + "..." if len(content) > 600 else content
                    parts.append(
                        f"\n[Fuente {i}] {title}\n"
                        f"URL: {url}\n"
                        f"Contenido: {content_preview}"
                    )
        return "\n".join(parts)

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        return self._query(query_bundle)

    def _get_prompt_modules(self):
        return {} 