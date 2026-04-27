"""
User Dashboard Service - Muestra todo lo que el usuario tiene en easycore
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)


class UserDashboardService:
    """
    Servicio para mostrar un dashboard completo del usuario:
    - Sus datos personales y de empleado
    - Clientes asignados
    - Propiedades asignadas
    - Operaciones y proyectos
    - Campañas creadas
    - Solicitudes de crédito
    - Vacaciones/permisos
    - Y más...
    """

    DASHBOARD_KEYWORDS = {
        'recordatorio', 'recordatorios', 'pendiente', 'pendientes', 'tareas', 'tarea',
        'que tengo', 'qué tengo', 'mis', 'mis tareas', 'mis pendientes', 'mi lista',
        'por hacer', 'por completar', 'incompleto', 'sin terminar', 'qué me falta',
        'qué debo', 'próximo', 'próximos', 'mi información', 'mis datos', 'mi dashboard',
        'qué tengo asignado', 'resumen', 'overview', 'estado', 'mi estatus'
    }

    def __init__(self, sql_database=None):
        """
        Args:
            sql_database: SQLDatabase instance from LlamaIndex
        """
        self.sql_database = sql_database
        logger.info("✓ UserDashboardService inicializado")

    def process_query(self, query: str, user_id: int, user_roles: List[str]) -> str:
        """
        Procesa una consulta y retorna el dashboard del usuario

        Args:
            query: Pregunta del usuario
            user_id: ID del usuario autenticado
            user_roles: Roles del usuario

        Returns:
            Respuesta formateada en markdown
        """
        if not self.sql_database:
            logger.error("❌ SQL Database no configurada")
            return "⚠️ Servicio no disponible temporalmente."

        try:
            logger.info(f"  📊 Generando dashboard para usuario ID: {user_id}")
            return self._get_user_dashboard(user_id)

        except Exception as e:
            logger.error(f"❌ Error procesando dashboard: {str(e)[:150]}", exc_info=True)
            return f"⚠️ Error al generar tu dashboard: {str(e)[:100]}"

    def _get_user_dashboard(self, user_id: int) -> str:
        """Genera dashboard completo del usuario"""
        try:
            response = "📊 **MI DASHBOARD EASYCORE**\n\n"

            # Información del usuario
            user_info = self._get_user_info(user_id)
            if user_info:
                response += user_info

            # 1. Clientes
            customers = self._get_user_customers(user_id)
            if customers:
                response += customers

            # 2. Propiedades asignadas
            properties = self._get_user_properties(user_id)
            if properties:
                response += properties

            # 3. Operaciones
            operations = self._get_user_operations(user_id)
            if operations:
                response += operations

            # 4. Proyectos
            projects = self._get_user_projects(user_id)
            if projects:
                response += projects

            # 5. Campañas
            campaigns = self._get_user_campaigns(user_id)
            if campaigns:
                response += campaigns

            # 6. Solicitudes de crédito
            credits = self._get_user_credits(user_id)
            if credits:
                response += credits

            # 7. Ofertas
            offers = self._get_user_offers(user_id)
            if offers:
                response += offers

            # 8. Vacaciones/Permisos
            leaves = self._get_user_leaves(user_id)
            if leaves:
                response += leaves

            # 9. Propiedades de terceros
            third_party = self._get_user_third_party_properties(user_id)
            if third_party:
                response += third_party

            # 10. Solicitudes de colaboración
            collabs = self._get_user_collaborations(user_id)
            if collabs:
                response += collabs

            # 11. Controles financieros
            financial = self._get_user_financial_controls(user_id)
            if financial:
                response += financial

            return response if len(response) > 50 else "ℹ️ No tienes datos asignados aún."

        except Exception as e:
            logger.error(f"❌ Error en _get_user_dashboard: {str(e)}")
            return f"⚠️ Error generando dashboard: {str(e)[:100]}"

    def _get_user_info(self, user_id: int) -> str:
        """Obtiene información del usuario"""
        try:
            sql = """
            SELECT
                u.id,
                u.name,
                u.email,
                u.code,
                u.state,
                c.name as country_name,
                e.job_position,
                e.phone
            FROM users u
            LEFT JOIN countries c ON u.country_id = c.id
            LEFT JOIN employees e ON u.id = e.user_id
            WHERE u.id = :user_id
            """

            results = self._execute_query(sql, {'user_id': user_id})

            if not results:
                return ""

            row = results[0]
            response = f"👤 **INFORMACIÓN DEL USUARIO**\n\n"
            response += f"- 📝 Nombre: {row['name']}\n"
            response += f"- 📧 Email: {row['email']}\n"
            response += f"- 🔖 Código: {row['code'] or '(sin asignar)'}\n"
            response += f"- 🌍 País: {row['country_name'] or '(sin asignar)'}\n"
            response += f"- 💼 Puesto: {row['job_position'] or '(sin asignar)'}\n"
            response += f"- 📞 Teléfono: {row['phone'] or '(sin asignar)'}\n"
            response += f"- 🔴 Estado: {row['state'].upper() if row['state'] else 'ACTIVO'}\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_user_info: {str(e)}")
            return ""

    def _get_user_customers(self, user_id: int) -> str:
        """Obtiene clientes del usuario"""
        try:
            sql = """
            SELECT COUNT(*) as total FROM customers WHERE user_id = :user_id
            """
            results = self._execute_query(sql, {'user_id': user_id})
            total = int(results[0]['total'] or 0) if results else 0

            if total == 0:
                return ""

            return f"👥 **Clientes:** {total} cliente{'s' if total != 1 else ''}\n"

        except Exception as e:
            logger.error(f"❌ Error en _get_user_customers: {str(e)}")
            return ""

    def _get_user_properties(self, user_id: int) -> str:
        """Obtiene propiedades asignadas"""
        try:
            sql = """
            SELECT COUNT(*) as total FROM property_assignments WHERE user_id = :user_id
            """
            results = self._execute_query(sql, {'user_id': user_id})
            total = int(results[0]['total'] or 0) if results else 0

            if total == 0:
                return ""

            return f"🏠 **Propiedades Asignadas:** {total} propiedad{'es' if total != 1 else ''}\n"

        except Exception as e:
            logger.error(f"❌ Error en _get_user_properties: {str(e)}")
            return ""

    def _get_user_operations(self, user_id: int) -> str:
        """Obtiene operaciones del usuario"""
        try:
            sql = """
            SELECT COUNT(*) as total FROM operations WHERE user_id = :user_id
            """
            results = self._execute_query(sql, {'user_id': user_id})
            total = int(results[0]['total'] or 0) if results else 0

            if total == 0:
                return ""

            return f"📋 **Operaciones:** {total} operación{'es' if total != 1 else ''}\n"

        except Exception as e:
            logger.error(f"❌ Error en _get_user_operations: {str(e)}")
            return ""

    def _get_user_projects(self, user_id: int) -> str:
        """Obtiene proyectos del usuario"""
        try:
            sql = """
            SELECT COUNT(*) as total FROM projects WHERE user_id = :user_id
            """
            results = self._execute_query(sql, {'user_id': user_id})
            total = int(results[0]['total'] or 0) if results else 0

            if total == 0:
                return ""

            return f"🚀 **Proyectos:** {total} proyecto{'s' if total != 1 else ''}\n"

        except Exception as e:
            logger.error(f"❌ Error en _get_user_projects: {str(e)}")
            return ""

    def _get_user_campaigns(self, user_id: int) -> str:
        """Obtiene campañas del usuario"""
        try:
            sql = """
            SELECT COUNT(*) as total FROM campaigns WHERE user_id = :user_id
            """
            results = self._execute_query(sql, {'user_id': user_id})
            total = int(results[0]['total'] or 0) if results else 0

            if total == 0:
                return ""

            return f"📢 **Campañas:** {total} campaña{'s' if total != 1 else ''}\n"

        except Exception as e:
            logger.error(f"❌ Error en _get_user_campaigns: {str(e)}")
            return ""

    def _get_user_credits(self, user_id: int) -> str:
        """Obtiene solicitudes de crédito"""
        try:
            sql = """
            SELECT COUNT(*) as total FROM credit_study_requests WHERE user_id = :user_id
            """
            results = self._execute_query(sql, {'user_id': user_id})
            total = int(results[0]['total'] or 0) if results else 0

            if total == 0:
                return ""

            return f"💰 **Solicitudes de Crédito:** {total} solicitud{'es' if total != 1 else ''}\n"

        except Exception as e:
            logger.error(f"❌ Error en _get_user_credits: {str(e)}")
            return ""

    def _get_user_offers(self, user_id: int) -> str:
        """Obtiene ofertas del usuario"""
        try:
            sql = """
            SELECT COUNT(*) as total FROM offers WHERE user_id = :user_id
            """
            results = self._execute_query(sql, {'user_id': user_id})
            total = int(results[0]['total'] or 0) if results else 0

            if total == 0:
                return ""

            return f"🎁 **Ofertas:** {total} oferta{'s' if total != 1 else ''}\n"

        except Exception as e:
            logger.error(f"❌ Error en _get_user_offers: {str(e)}")
            return ""

    def _get_user_leaves(self, user_id: int) -> str:
        """Obtiene vacaciones/permisos"""
        try:
            sql = """
            SELECT COUNT(*) as total, request_status FROM leave_requests
            WHERE user_id = :user_id
            GROUP BY request_status
            """
            results = self._execute_query(sql, {'user_id': user_id})

            if not results:
                return ""

            total = sum(int(row['total'] or 0) for row in results)
            if total == 0:
                return ""

            pending = sum(int(row['total'] or 0) for row in results if row['request_status'] == 'pending')

            response = f"🏖️ **Vacaciones/Permisos:** {total} total"
            if pending > 0:
                response += f" (⏳ {pending} pendiente{'s' if pending != 1 else ''})"
            response += "\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_user_leaves: {str(e)}")
            return ""

    def _get_user_third_party_properties(self, user_id: int) -> str:
        """Obtiene propiedades de terceros"""
        try:
            sql = """
            SELECT COUNT(*) as total FROM third_party_properties WHERE user_id = :user_id
            """
            results = self._execute_query(sql, {'user_id': user_id})
            total = int(results[0]['total'] or 0) if results else 0

            if total == 0:
                return ""

            return f"🏘️ **Propiedades de Terceros:** {total} propiedad{'es' if total != 1 else ''}\n"

        except Exception as e:
            logger.error(f"❌ Error en _get_user_third_party_properties: {str(e)}")
            return ""

    def _get_user_collaborations(self, user_id: int) -> str:
        """Obtiene solicitudes de colaboración"""
        try:
            sql = """
            SELECT COUNT(*) as total FROM collaboration_requests WHERE user_id = :user_id
            """
            results = self._execute_query(sql, {'user_id': user_id})
            total = int(results[0]['total'] or 0) if results else 0

            if total == 0:
                return ""

            return f"🤝 **Colaboraciones:** {total} colaboración{'es' if total != 1 else ''}\n"

        except Exception as e:
            logger.error(f"❌ Error en _get_user_collaborations: {str(e)}")
            return ""

    def _get_user_financial_controls(self, user_id: int) -> str:
        """Obtiene controles financieros"""
        try:
            sql = """
            SELECT COUNT(*) as total FROM financial_controls WHERE user_id = :user_id
            """
            results = self._execute_query(sql, {'user_id': user_id})
            total = int(results[0]['total'] or 0) if results else 0

            if total == 0:
                return ""

            return f"💵 **Controles Financieros:** {total} control{'es' if total != 1 else ''}\n"

        except Exception as e:
            logger.error(f"❌ Error en _get_user_financial_controls: {str(e)}")
            return ""

    def _execute_query(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        """Ejecuta query SQL y retorna resultados como lista de dicts"""
        try:
            if not self.sql_database:
                raise ValueError("SQL Database no configurada")

            connection = self.sql_database._engine.connect()

            if params:
                result = connection.execute(text(sql), params)
            else:
                result = connection.execute(text(sql))

            rows = result.fetchall()
            connection.close()

            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error(f"❌ Error ejecutando SQL: {str(e)}")
            raise
