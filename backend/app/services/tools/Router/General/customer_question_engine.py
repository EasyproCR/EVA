"""
Customer Question Engine - Responde preguntas sobre clientes personales
"""

import logging
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from .customer_data_service import CustomerDataService

logger = logging.getLogger(__name__)

class CustomerQuestionEngine(BaseQueryEngine):
    """
    Query Engine para responder preguntas sobre clientes personales (necesidades y direcciones).
    """

    # Keywords para detectar preguntas sobre clientes
    CUSTOMER_KEYWORDS = {
        'cliente', 'clientes', 'personas', 'comprador', 'compradores',
        'buscan', 'busca', 'necesitan', 'necesita', 'viven en', 'son de',
        'quieren', 'quiere'
    }

    def __init__(self, sql_database=None):
        super().__init__(callback_manager=CallbackManager([]))
        self.sql_database = sql_database
        self.user_roles = []
        self.data_service = CustomerDataService(sql_database)
        logger.info("✓ CustomerQuestionEngine inicializado")

    def _is_customer_question(self, query: str) -> bool:
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.CUSTOMER_KEYWORDS)

    def set_user_roles(self, roles):
        self.user_roles = roles if roles else []
        logger.info(f"  👤 Roles asignados a CustomerQuestionEngine: {self.user_roles}")

    def _has_permission(self) -> bool:
        if not self.user_roles:
            return False
            
        roles_permitidos = {'servicio_al_cliente', 'master', 'admin', 'super_admin'}
        user_roles_set = {str(r).lower().strip() for r in self.user_roles}
        return bool(roles_permitidos.intersection(user_roles_set))

    def _query(self, query_bundle: QueryBundle) -> Response:
        query = query_bundle.query_str
        logger.info(f"👥 Customer Question: {query}")

        if not self._is_customer_question(query):
            return Response(response="")

        if not self._has_permission():
            logger.warning(f"⚠️ Acceso denegado a Clientes Personales para roles: {self.user_roles}")
            return Response(
                response="🔒 **Acceso Denegado**\n\nSolo el departamento de **Servicio al Cliente** y administradores están autorizados para buscar en la base de datos de clientes personales."
            )

        try:
            response_text = self.data_service.process_query(query)
            return Response(response=response_text)
        except Exception as e:
            logger.error(f"❌ Error en CustomerDataService: {str(e)}", exc_info=True)
            return Response(response=f"⚠️ Error procesando tu consulta de clientes: {str(e)}")

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        return self._query(query_bundle)

    def _get_prompt_modules(self):
        return {}
