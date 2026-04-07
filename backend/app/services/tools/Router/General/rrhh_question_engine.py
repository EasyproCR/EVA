"""
RRHH Question Answering Engine - Responde preguntas sobre RRHH con control de acceso
Solo usuarios con rol 'rrhh' o 'super_admin' pueden acceder a esta información
"""

import logging
from typing import Optional
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from .rrhh_data_service import RrhhDataService

logger = logging.getLogger(__name__)


class RrhhQuestionEngine(BaseQueryEngine):
    """
    Query Engine para responder preguntas sobre RRHH con control de acceso.

    Solo usuarios con rol 'rrhh' o 'super_admin' pueden acceder a:
    - Expedientes de empleados
    - Vacaciones y permisos
    - Solicitudes de crédito/préstamo
    - Pautas y políticas
    - Recordatorios administrativos
    """

    # Keywords para detectar preguntas sobre RRHH
    RRHH_KEYWORDS = {
        # Expediente/empleados
        'expediente', 'expedientes', 'empleado', 'empleados', 'perfil', 'perfiles',
        'contrato', 'contratos', 'puesto', 'puestos', 'salario', 'salary',
        'datos empleado', 'información empleado', 'ficha empleado',

        # Vacaciones/permisos
        'vacacion', 'vacaciones', 'permiso', 'permisos', 'licencia', 'licencias',
        'días libres', 'absent', 'ausencia', 'incapacidad',

        # Créditos/préstamos
        'crédito', 'credito', 'préstamo', 'prestamo', 'adelanto', 'loan', 'credit',
        'solicitud de crédito', 'solicitud de préstamo',

        # Pautas/políticas
        'pauta', 'pautas', 'política', 'politica', 'políticas', 'guideline',
        'código conducta', 'codigo conducta', 'procedimiento', 'procedimientos',
        'política interna', 'norma', 'normas', 'reglamento',

        # Recordatorios y alertas
        'recordatorio', 'recordatorios', 'tatiana', 'rrhh', 'recursos humanos',
        'alerta', 'alertas', 'pendiente', 'pendientes', 'oendiente', 'oendientes',
        'tarea', 'tareas', 'administrador',

        # Cumpleaños
        'cumpleaño', 'cumpleaños', 'nacimiento', 'birthday', 'aniversario'
    }

    def __init__(self, sql_database=None):
        """
        Args:
            sql_database: SQLDatabase instance from LlamaIndex (para ejecutar queries)
        """
        super().__init__(callback_manager=CallbackManager([]))
        self.sql_database = sql_database
        self.user_roles = []  # Se asigna desde el router
        self.data_service = RrhhDataService(sql_database)
        logger.info("✓ RrhhQuestionEngine inicializado")

    def _is_rrhh_question(self, query: str) -> bool:
        """Detecta si la pregunta es sobre RRHH basada en keywords"""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.RRHH_KEYWORDS)

    def _has_rrhh_access(self) -> bool:
        """Verifica si el usuario tiene acceso a RRHH"""
        if not self.user_roles:
            return False

        roles = [str(r).lower().strip() for r in self.user_roles]
        allowed_roles = {
            'super_admin', 'rrhh'
        }

        return any(role in allowed_roles for role in roles)

    def _query(self, query_bundle: QueryBundle) -> Response:
        """
        Procesa preguntas sobre RRHH con control de acceso.
        Si el usuario tiene permiso, construye y ejecuta queries RRHH.
        """
        query = query_bundle.query_str
        logger.info(f"📋 RRHH Question: {query}")

        # Verificar si es realmente una pregunta sobre RRHH
        if not self._is_rrhh_question(query):
            logger.info(f"  ℹ️ No es pregunta sobre RRHH, delegando a otro engine")
            return Response(response="")  # Retorna vacío para que otro engine lo procese

        logger.info(f"  🔍 Detectada pregunta sobre RRHH")

        # Verificar acceso
        if not self._has_rrhh_access():
            logger.warning(f"  ⚠️ Usuario sin acceso a RRHH - Roles: {self.user_roles}")
            access_denied_msg = (
                "❌ No tienes permiso para acceder a información de RRHH.\n"
                "Por favor, contacta con el área de RRHH para solicitar estos datos."
            )
            return Response(response=access_denied_msg)

        logger.info(f"  ✅ Usuario autorizado para RRHH")

        # Si tiene acceso, usar RrhhDataService para procesar
        try:
            response_text = self.data_service.process_query(query, self.user_roles)
            logger.info(f"  📊 Respuesta generada desde RrhhDataService")
            return Response(response=response_text)
        except Exception as e:
            logger.error(f"  ❌ Error en RrhhDataService: {str(e)}", exc_info=True)
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
