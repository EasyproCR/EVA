"""
User Dashboard Question Engine - Responde preguntas sobre el dashboard del usuario
"""

import logging
from typing import Optional
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from .pending_reminders_service import UserDashboardService

logger = logging.getLogger(__name__)


class PendingRemindersQuestionEngine(BaseQueryEngine):
    """
    Query Engine para responder preguntas sobre el dashboard/datos del usuario.

    Acceso: Todos los usuarios autenticados (acceso abierto)
    """

    # Keywords para detectar preguntas sobre dashboard/datos del usuario
    REMINDERS_KEYWORDS = {
        'recordatorio', 'recordatorios', 'pendiente', 'pendientes', 'tareas', 'tarea',
        'que tengo', 'qué tengo', 'mis', 'mis tareas', 'mis pendientes', 'mi lista',
        'por hacer', 'por completar', 'incompleto', 'sin terminar', 'qué me falta',
        'qué debo', 'próximo', 'próximos', 'vacaciones pendientes', 'créditos pendientes',
        'mi información', 'mis datos', 'mi dashboard', 'qué tengo asignado', 'mi resumen'
    }

    def __init__(self, sql_database=None):
        """
        Args:
            sql_database: SQLDatabase instance from LlamaIndex (para ejecutar queries)
        """
        super().__init__(callback_manager=CallbackManager([]))
        self.sql_database = sql_database
        self.user_roles = []  # Se asigna desde el router
        self.user_id = None  # Se asigna desde el router
        self.data_service = UserDashboardService(sql_database)
        logger.info("✓ PendingRemindersQuestionEngine inicializado")

    def _is_reminders_question(self, query: str) -> bool:
        """Detecta si la pregunta es sobre recordatorios/dashboard basada en keywords"""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.REMINDERS_KEYWORDS)

    def _has_reminders_access(self) -> bool:
        """Verifica si el usuario tiene acceso a recordatorios - ACCESO ABIERTO"""
        # Acceso abierto para todos los usuarios autenticados
        return True

    def _query(self, query_bundle: QueryBundle) -> Response:
        """
        Procesa preguntas sobre recordatorios/dashboard con control de acceso.
        """
        query = query_bundle.query_str
        logger.info(f"📋 Reminders Question: {query}")

        # Verificar si es realmente una pregunta sobre recordatorios
        if not self._is_reminders_question(query):
            logger.info(f"  ℹ️ No es pregunta sobre recordatorios, delegando a otro engine")
            return Response(response="")  # Retorna vacío para que otro engine lo procese

        logger.info(f"  🔍 Detectada pregunta sobre recordatorios/datos del usuario")

        # Verificar acceso
        if not self._has_reminders_access():
            logger.warning(f"  ⚠️ Usuario sin acceso a recordatorios")
            access_denied_msg = (
                "❌ No tienes permiso para acceder a tus recordatorios.\n"
                "Por favor, contacta con tu administrador."
            )
            return Response(response=access_denied_msg)

        logger.info(f"  ✅ Usuario autorizado para recordatorios")

        # Verificar que tenga user_id
        if not self.user_id:
            logger.error(f"  ❌ user_id no asignado")
            return Response(response="⚠️ No se pudo identificar tu usuario. Por favor, intenta de nuevo.")

        # Si tiene acceso, usar UserDashboardService para procesar
        try:
            response_text = self.data_service.process_query(query, self.user_id, self.user_roles)
            logger.info(f"  📊 Respuesta generada desde UserDashboardService")
            return Response(response=response_text)
        except Exception as e:
            logger.error(f"  ❌ Error en UserDashboardService: {str(e)}", exc_info=True)
            return Response(response=f"⚠️ Error procesando tu consulta: {str(e)}")

    def set_user_roles(self, roles):
        """Setter para asignar roles del usuario desde el router"""
        self.user_roles = roles if roles else []
        logger.info(f"  👤 Roles asignados: {self.user_roles}")

    def set_user_id(self, user_id):
        """Setter para asignar ID del usuario desde el router"""
        self.user_id = user_id
        logger.info(f"  👤 User ID asignado: {user_id}")

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        """Versión async de _query."""
        return self._query(query_bundle)

    def _get_prompt_modules(self):
        """Requerido por BaseQueryEngine."""
        return {}

