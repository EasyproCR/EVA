"""
Customer Reminders Question Engine - Responde preguntas sobre recordatorios de clientes
"""

import logging
from typing import Optional
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from .customer_reminders_service import CustomerRemindersService

logger = logging.getLogger(__name__)


class CustomerRemindersQuestionEngine(BaseQueryEngine):
    """
    Query Engine para responder preguntas sobre recordatorios de clientes.

    Acceso: Todos los usuarios autenticados
    """

    # Keywords para detectar preguntas sobre recordatorios de clientes
    CUSTOMER_KEYWORDS = {
        'cliente', 'clientes', 'cita', 'citas', 'seguimiento', 'seguimientos',
        'agendar', 'agendar cita', 'recordatorio', 'recordatorios', 'contacto',
        'contactos', 'llamada', 'reunión', 'llamadas', 'reuniones', 'próxima cita',
        'mis clientes', 'clientes pendientes', 'clientes sin cita', 'clientes sin seguimiento'
    }

    def __init__(self, sql_database=None):
        """
        Args:
            sql_database: SQLDatabase instance from LlamaIndex
        """
        super().__init__(callback_manager=CallbackManager([]))
        self.sql_database = sql_database
        self.user_roles = []
        self.user_id = None
        self.data_service = CustomerRemindersService(sql_database)
        logger.info("✓ CustomerRemindersQuestionEngine inicializado")

    def _is_customer_question(self, query: str) -> bool:
        """Detecta si la pregunta es sobre clientes/recordatorios basada en keywords"""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.CUSTOMER_KEYWORDS)

    def _has_customer_access(self) -> bool:
        """Verifica si el usuario tiene acceso - ACCESO ABIERTO"""
        return True

    def _query(self, query_bundle: QueryBundle) -> Response:
        """
        Procesa preguntas sobre recordatorios de clientes.
        """
        query = query_bundle.query_str
        logger.info(f"📞 Customer Reminders Question: {query}")

        # Verificar si es realmente una pregunta sobre clientes
        if not self._is_customer_question(query):
            logger.info(f"  ℹ️ No es pregunta sobre clientes, delegando a otro engine")
            return Response(response="")

        logger.info(f"  🔍 Detectada pregunta sobre clientes/recordatorios")

        # Verificar acceso
        if not self._has_customer_access():
            logger.warning(f"  ⚠️ Usuario sin acceso")
            return Response(response="❌ No tienes permiso para acceder a esta información.")

        logger.info(f"  ✅ Usuario autorizado")

        # Verificar que tenga user_id
        if not self.user_id:
            logger.error(f"  ❌ user_id no asignado")
            return Response(response="⚠️ No se pudo identificar tu usuario.")

        # Procesar consulta
        try:
            response_text = self.data_service.process_query(query, self.user_id, self.user_roles)
            logger.info(f"  📊 Respuesta generada desde CustomerRemindersService")
            return Response(response=response_text)
        except Exception as e:
            logger.error(f"  ❌ Error: {str(e)}", exc_info=True)
            return Response(response=f"⚠️ Error procesando tu consulta: {str(e)}")

    def set_user_roles(self, roles):
        """Setter para asignar roles del usuario"""
        self.user_roles = roles if roles else []

    def set_user_id(self, user_id):
        """Setter para asignar ID del usuario"""
        self.user_id = user_id
        logger.info(f"  👤 User ID asignado: {user_id}")

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        """Versión async de _query."""
        return self._query(query_bundle)

    def _get_prompt_modules(self):
        """Requerido por BaseQueryEngine."""
        return {}
