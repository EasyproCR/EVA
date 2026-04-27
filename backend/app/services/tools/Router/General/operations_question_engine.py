"""
Operations Question Answering Engine - Responde preguntas sobre citas y operaciones
Solo usuarios con rol 'operations' o 'super_admin' pueden acceder a esta información
"""

import logging
from typing import Optional
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from .operations_data_service import OperationsDataService

logger = logging.getLogger(__name__)


class OperationsQuestionEngine(BaseQueryEngine):
    """
    Query Engine para responder preguntas sobre citas y operaciones con control de acceso.

    Solo usuarios con rol 'operations' o 'super_admin' pueden acceder a:
    - Citas pendientes
    - Citas con clientes específicos
    - Recordatorios de operaciones
    """

    # Keywords para detectar preguntas sobre operaciones/citas
    OPERATIONS_KEYWORDS = {
        # Citas/reuniones
        'cita', 'citas', 'appointment', 'appointments', 'reunión', 'reuniones',
        'meeting', 'meetings', 'agendado', 'agendada', 'programado', 'programada',

        # Estado de citas
        'pendiente', 'pendientes', 'próximo', 'próxima', 'upcoming', 'scheduled',
        'tengo cita', 'tengo citas', 'me he', 'tengo una cita',

        # Clientes
        'cliente', 'clientes', 'customer', 'customers', 'empresa', 'empresas',
        'con ', 'de ', 'contacto', 'contactos',

        # Palabras de contexto
        'operaciones', 'ops', 'alejandra'
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
        self.data_service = OperationsDataService(sql_database)
        logger.info("✓ OperationsQuestionEngine inicializado")

    def _is_operations_question(self, query: str) -> bool:
        """Detecta si la pregunta es sobre operaciones/citas basada en keywords"""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.OPERATIONS_KEYWORDS)

    def _has_operations_access(self) -> bool:
        """Verifica si el usuario tiene acceso a operaciones"""
        if not self.user_roles:
            return False

        roles = [str(r).lower().strip() for r in self.user_roles]
        allowed_roles = {
            'super_admin', 'operations', 'gerente'
        }

        return any(role in allowed_roles for role in roles)

    def _query(self, query_bundle: QueryBundle) -> Response:
        """
        Procesa preguntas sobre operaciones/citas con control de acceso.
        Si el usuario tiene permiso, construye y ejecuta queries de citas.
        """
        query = query_bundle.query_str
        logger.info(f"📅 Operations Question: {query}")

        # Verificar si es realmente una pregunta sobre operaciones
        if not self._is_operations_question(query):
            logger.info(f"  ℹ️ No es pregunta sobre operaciones, delegando a otro engine")
            return Response(response="")  # Retorna vacío para que otro engine lo procese

        logger.info(f"  🔍 Detectada pregunta sobre operaciones")

        # Verificar acceso
        if not self._has_operations_access():
            logger.warning(f"  ⚠️ Usuario sin acceso a operaciones - Roles: {self.user_roles}")
            access_denied_msg = (
                "❌ No tienes permiso para acceder a información de operaciones.\n"
                "Por favor, contacta con el área de operaciones para solicitar estos datos."
            )
            return Response(response=access_denied_msg)

        logger.info(f"  ✅ Usuario autorizado para operaciones")

        # Si no tenemos user_id, no podemos filtrar citas personales
        if not self.user_id:
            logger.warning(f"  ⚠️ User ID no disponible")
            return Response(response="⚠️ No pudimos identificar tu usuario. Por favor, intenta de nuevo.")

        # Si tiene acceso, usar OperationsDataService para procesar
        try:
            response_text = self.data_service.process_query(query, self.user_id)
            logger.info(f"  📊 Respuesta generada desde OperationsDataService")
            return Response(response=response_text)
        except Exception as e:
            logger.error(f"  ❌ Error en OperationsDataService: {str(e)}", exc_info=True)
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
