"""
Posts Question Answering Engine - Responde preguntas sobre posts/publicaciones en redes sociales
"""

import logging
from typing import Optional
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from .posts_data_service import PostsDataService

logger = logging.getLogger(__name__)


class PostsQuestionEngine(BaseQueryEngine):
    """
    Query Engine para responder preguntas sobre posts/publicaciones en redes sociales.

    Acceso: Super admins, administradores, usuarios de marketing/operaciones
    Acceso por roles: super_admin, administrator, marketing, operaciones, sales
    """

    # Keywords para detectar preguntas sobre posts
    POSTS_KEYWORDS = {
        'post', 'posts', 'publicación', 'publicaciones', 'social', 'sociales',
        'instagram', 'facebook', 'twitter', 'tiktok', 'linkedin', 'youtube',
        'red social', 'redes sociales', 'reel', 'reels', 'feed', 'story', 'stories',
        'contenido', 'publicar', 'publicado', 'trending', 'engagement', 'reach',
        'campaña social', 'campañas sociales', 'reacción', 'reacciones',
        'comentario', 'comentarios', 'compartir', 'compartido', 'share', 'shares',
        'vista', 'vistas', 'visualización', 'visualizaciones'
    }

    def __init__(self, sql_database=None):
        """
        Args:
            sql_database: SQLDatabase instance from LlamaIndex (para ejecutar queries)
        """
        super().__init__(callback_manager=CallbackManager([]))
        self.sql_database = sql_database
        self.user_roles = []  # Se asigna desde el router
        self.data_service = PostsDataService(sql_database)
        logger.info("✓ PostsQuestionEngine inicializado")

    def _is_posts_question(self, query: str) -> bool:
        """Detecta si la pregunta es sobre posts basada en keywords"""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.POSTS_KEYWORDS)

    def _has_posts_access(self) -> bool:
        """Verifica si el usuario tiene acceso a posts/publicaciones - ACCESO ABIERTO"""
        # Acceso abierto para todos los usuarios
        return True

    def _query(self, query_bundle: QueryBundle) -> Response:
        """
        Procesa preguntas sobre posts con control de acceso.
        Si el usuario tiene permiso, construye y ejecuta queries.
        """
        query = query_bundle.query_str
        logger.info(f"📱 Posts Question: {query}")

        # Verificar si es realmente una pregunta sobre posts
        if not self._is_posts_question(query):
            logger.info(f"  ℹ️ No es pregunta sobre posts, delegando a otro engine")
            return Response(response="")  # Retorna vacío para que otro engine lo procese

        logger.info(f"  🔍 Detectada pregunta sobre posts/publicaciones")

        # Verificar acceso
        if not self._has_posts_access():
            logger.warning(f"  ⚠️ Usuario sin acceso a posts")
            access_denied_msg = (
                "❌ No tienes permiso para acceder a información de posts/publicaciones.\n"
                "Por favor, contacta con tu administrador."
            )
            return Response(response=access_denied_msg)

        logger.info(f"  ✅ Usuario autorizado para posts")

        # Si tiene acceso, usar PostsDataService para procesar
        try:
            response_text = self.data_service.process_query(query, self.user_roles)
            logger.info(f"  📊 Respuesta generada desde PostsDataService")
            return Response(response=response_text)
        except Exception as e:
            logger.error(f"  ❌ Error en PostsDataService: {str(e)}", exc_info=True)
            return Response(response=f"⚠️ Error procesando tu consulta: {str(e)}")

    def set_user_roles(self, roles):
        """Setter para asignar roles del usuario desde el router"""
        self.user_roles = roles if roles else []
        logger.info(f"  👤 Roles asignados: {self.user_roles}")

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        """Versión async de _query."""
        return self._query(query_bundle)

    def _get_prompt_modules(self):
        """Requerido por BaseQueryEngine."""
        return {}
