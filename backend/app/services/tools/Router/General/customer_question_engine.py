"""
Customer Question Engine - Responde preguntas sobre clientes personales ADM
SIEMPRE usa CustomerDataService para buscar en personal_customers.
Solo retorna clientes cuyos asesores tienen rol admin/administrator/super_admin.
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
    Query Engine para responder preguntas sobre clientes personales ADM.
    La restriccion de solo mostrar clientes admin se aplica en el SQL
    (INNER JOIN roles WHERE name IN ('administrator','super_admin','admin')).
    """

    # Keywords que identifican una pregunta sobre clientes
    CUSTOMER_KEYWORDS = {
        'cliente', 'clientes', 'personas', 'comprador', 'compradores',
        'buscan', 'busca', 'necesitan', 'necesita', 'viven en', 'son de',
        'quieren', 'quiere', 'personal_customers'
    }

    # Roles con acceso permitido
    ALLOWED_ROLES = {
        'servicio_al_cliente', 'master', 'admin', 'super_admin',
        'administrator', 'administrador', 'gerente'
    }

    def __init__(self, sql_database=None):
        super().__init__(callback_manager=CallbackManager([]))
        self.sql_database = sql_database
        self.user_roles = []
        # Flag para bypass de permiso cuando se llama desde hardcoded routing
        self._bypass_permission = False
        self.data_service = CustomerDataService(sql_database)
        logger.info("CustomerQuestionEngine inicializado")

    def set_user_roles(self, roles):
        self.user_roles = roles if roles else []
        logger.info(f"Roles asignados a CustomerQuestionEngine: {self.user_roles}")

    def set_bypass_permission(self, bypass: bool = True):
        """Permite bypass del check de roles cuando el router ya validó el acceso."""
        self._bypass_permission = bypass

    def _is_customer_question(self, query: str) -> bool:
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.CUSTOMER_KEYWORDS)

    def _has_permission(self) -> bool:
        # Si bypass activo, permitir siempre (el router ya valido)
        if self._bypass_permission:
            return True
        # Sin roles asignados -> denegar
        if not self.user_roles:
            logger.warning("CustomerQuestionEngine: sin roles, denegando acceso")
            return False
        user_roles_set = {str(r).lower().strip() for r in self.user_roles}
        has_perm = bool(self.ALLOWED_ROLES.intersection(user_roles_set))
        logger.info(f"Permiso clientes: {has_perm} | roles={user_roles_set}")
        return has_perm

    def _query(self, query_bundle: QueryBundle) -> Response:
        query = query_bundle.query_str
        logger.info(f"CustomerQuestionEngine._query: '{query}'")
        logger.info(f"  roles={self.user_roles} | bypass={self._bypass_permission}")

        # Verificar permiso
        if not self._has_permission():
            logger.warning(f"Acceso denegado. Roles: {self.user_roles}")
            return Response(
                response=(
                    "Acceso Denegado\n\n"
                    "Solo administradores y Servicio al Cliente pueden "
                    "consultar la base de datos de clientes personales."
                )
            )

        try:
            response_text = self.data_service.process_query(query)
            logger.info(f"Respuesta CustomerDataService: {response_text[:100]}...")
            return Response(response=response_text)
        except Exception as e:
            logger.error(f"Error en CustomerDataService: {str(e)}", exc_info=True)
            return Response(response=f"Error procesando consulta de clientes: {str(e)}")

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        return self._query(query_bundle)

    def _get_prompt_modules(self):
        return {}
