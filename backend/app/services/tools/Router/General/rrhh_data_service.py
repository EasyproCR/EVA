"""
RRHH Data Service - Construye y procesa consultas de RRHH con respuestas formateadas
"""

import logging
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)


class RrhhDataService:
    """
    Servicio para procesar consultas RRHH:
    - Classifica preguntas naturales en categorías RRHH
    - Construye queries SQL
    - Formatea respuestas legibles
    """

    # Keywords por categoría
    EMPLOYEES_KEYWORDS = {
        'expediente', 'expedientes', 'empleado', 'empleados', 'perfil', 'perfiles',
        'contrato', 'contratos', 'puesto', 'puestos', 'salario', 'datos empleado',
        'información empleado', 'ficha empleado', 'staff', 'personal'
    }

    LEAVES_KEYWORDS = {
        'vacacion', 'vacaciones', 'permiso', 'permisos', 'licencia', 'licencias',
        'días libres', 'ausencia', 'incapacidad', 'baja', 'descanso', 'leave',
        'solicitud de vacaciones', 'solicitud de permiso'
    }

    LOANS_KEYWORDS = {
        'crédito', 'credito', 'préstamo', 'prestamo', 'adelanto', 'loan', 'credit',
        'solicitud de crédito', 'solicitud de préstamo', 'solicitud de adelanto'
    }

    POLICIES_KEYWORDS = {
        'pauta', 'pautas', 'política', 'politica', 'políticas', 'guideline',
        'código conducta', 'codigo conducta', 'procedimiento', 'procedimientos',
        'política interna', 'norma', 'normas', 'reglamento', 'reglas'
    }

    REMINDERS_KEYWORDS = {
        'recordatorio', 'recordatorios', 'tatiana', 'tarea', 'tareas', 'pendiente',
        'debido', 'vencimiento', 'administrador', 'reminder', 'alerta', 'alertas'
    }

    def __init__(self, sql_database=None):
        """
        Args:
            sql_database: SQLDatabase instance from LlamaIndex
        """
        self.sql_database = sql_database
        logger.info("✓ RrhhDataService inicializado")

    def process_query(self, query: str, user_roles: List[str]) -> str:
        """
        Procesa una consulta RRHH y retorna respuesta formateada

        Args:
            query: Pregunta del usuario
            user_roles: Roles del usuario (para logging)

        Returns:
            Respuesta formateada en markdown
        """
        if not self.sql_database:
            logger.error("❌ SQL Database no configurada en RrhhDataService")
            return "⚠️ Servicio de RRHH no disponible temporalmente. Por favor, intenta más tarde."

        try:
            # Clasificar tipo de consulta
            query_type = self._classify_query(query)
            logger.info(f"  📁 Tipo de consulta: {query_type}")

            # Procesar según tipo
            if query_type == "EMPLOYEES":
                return self._process_employees_query(query, user_roles)
            elif query_type == "LEAVES":
                return self._process_leaves_query(query, user_roles)
            elif query_type == "LOANS":
                return self._process_loans_query(query, user_roles)
            elif query_type == "POLICIES":
                return self._process_policies_query(query, user_roles)
            elif query_type == "REMINDERS":
                return self._process_reminders_query(query, user_roles)
            else:
                return "❓ No pude clasificar tu pregunta de RRHH. ¿Podrías ser más específico?"

        except Exception as e:
            logger.error(f"❌ Error procesando query RRHH: {str(e)[:150]}", exc_info=True)
            return f"⚠️ Error al procesar tu consulta: {str(e)[:100]}"

    def _classify_query(self, query: str) -> Optional[str]:
        """
        Clasifica la pregunta en categoría RRHH usando keywords
        """
        query_lower = query.lower()

        if any(kw in query_lower for kw in self.EMPLOYEES_KEYWORDS):
            return "EMPLOYEES"
        elif any(kw in query_lower for kw in self.LEAVES_KEYWORDS):
            return "LEAVES"
        elif any(kw in query_lower for kw in self.LOANS_KEYWORDS):
            return "LOANS"
        elif any(kw in query_lower for kw in self.POLICIES_KEYWORDS):
            return "POLICIES"
        elif any(kw in query_lower for kw in self.REMINDERS_KEYWORDS):
            return "REMINDERS"

        return None

    def _execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Ejecuta una query SQL segura con manejo robusto de errores
        """
        if not sql or not self.sql_database:
            logger.warning("⚠️ SQL vacío o DB no disponible")
            return []

        try:
            engine = self.sql_database._engine
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = result.mappings().all()
                return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"❌ Error SQL ({type(e).__name__}): {str(e)[:150]}")
            return []

    def _process_employees_query(self, query: str, user_roles: List[str]) -> str:
        """
        Procesa consulta sobre expedientes de empleados
        """
        logger.info(f"  👤 Procesando query de EMPLEADOS: {query}")

        try:
            query_lower = query.lower()

            # Detectar lista de todos
            ver_todos = any(kw in query_lower for kw in ['todos', 'lista', 'listado', 'hay', 'cuantos', 'cuántos'])

            if ver_todos:
                sql = "SELECT id, name, email, job_position, phone_number FROM employees WHERE contract_status = 1 ORDER BY name LIMIT 50"
                results = self._execute_query(sql)

                if not results:
                    return "ℹ️ No hay empleados activos en el sistema."

                response = f"📋 **Lista de Empleados Activos** ({len(results)})\n\n"
                for emp in results:
                    response += f"- **{emp.get('name', 'N/A')}** - {emp.get('job_position', 'Sin puesto')}\n"
                    response += f"  📧 {emp.get('email', 'N/A')} | 📞 {emp.get('phone_number', 'N/A')}\n"

                return response

            # Búsqueda específica
            search_name = self._extract_search_term(query, ["expediente", "empleado", "datos"])
            if search_name:
                logger.info(f"  🔍 Buscando empleado: '{search_name}'")

                # Búsqueda simple sin complicaciones
                sql = f"""
                SELECT id, name, email, phone_number, job_position, profession,
                       national_id, address, birthday, marital_status, contract
                FROM employees
                WHERE UPPER(name) LIKE UPPER('%{search_name}%')
                AND contract_status = 1
                ORDER BY name
                LIMIT 1
                """

                logger.info(f"  📝 Buscando: UPPER(name) LIKE UPPER('%{search_name}%')")
                results = self._execute_query(sql)

                if not results:
                    # Si no encuentra activos, busca en TODOS (incluyendo inactivos)
                    sql_all = f"""
                    SELECT id, name, email, phone_number, job_position, profession,
                           national_id, address, birthday, marital_status, contract
                    FROM employees
                    WHERE UPPER(name) LIKE UPPER('%{search_name}%')
                    ORDER BY name
                    LIMIT 1
                    """
                    results = self._execute_query(sql_all)

                    if not results:
                        # Como último recurso, listar todos los empleados
                        logger.warning(f"  ❌ No encontrado: {search_name}")
                        all_employees_sql = "SELECT id, name FROM employees ORDER BY name LIMIT 30"
                        all_emps = self._execute_query(all_employees_sql)
                        emp_list = '\n'.join([f"  • {e.get('name', 'N/A')}" for e in all_emps])
                        return (
                            f"❌ No encontré empleado '{search_name}' en el sistema.\n\n"
                            f"📋 Empleados disponibles:\n{emp_list}\n\n"
                            f"¿Quizás quisiste decir alguno de estos? Intenta de nuevo con el nombre exacto."
                        )

                emp = results[0]
                response = f"📋 **Expediente: {emp.get('name', 'N/A')}**\n\n"
                response += f"- **Email:** {emp.get('email', 'N/A')}\n"
                response += f"- **Teléfono:** {emp.get('phone_number', 'N/A')}\n"
                response += f"- **Puesto:** {emp.get('job_position', 'N/A')}\n"
                response += f"- **Profesión:** {emp.get('profession', 'N/A')}\n"
                response += f"- **Cédula:** {emp.get('national_id', 'N/A')}\n"
                response += f"- **Dirección:** {emp.get('address', 'N/A')}\n"
                response += f"- **Cumpleaños:** {emp.get('birthday', 'N/A')}\n"
                response += f"- **Estado Civil:** {emp.get('marital_status', 'N/A')}\n"
                response += f"- **Tipo Contrato:** {emp.get('contract', 'N/A')}\n"

                return response

            return "❓ Pregunta por un empleado específico"

        except Exception as e:
            logger.error(f"❌ Error en empleados: {str(e)[:150]}")
            return f"⚠️ Error: {str(e)[:80]}"

    def _process_leaves_query(self, query: str, user_roles: List[str]) -> str:
        """
        Procesa consulta sobre vacaciones
        """
        logger.info(f"  🏖️ Procesando query de VACACIONES: {query}")

        try:
            state_filter = self._detect_state_filter(query)

            sql = f"""
            SELECT lr.id, u.name as empleado_nombre, lr.request_type as tipo,
                   lr.request_status as estado, lr.start_date as inicio,
                   lr.end_date as fin, lr.total_days as dias_totales
            FROM leave_requests lr
            LEFT JOIN users u ON lr.user_id = u.id
            WHERE 1=1
            {f"AND lr.request_status = '{state_filter}'" if state_filter else ""}
            ORDER BY lr.start_date DESC
            LIMIT 20
            """

            results = self._execute_query(sql)

            if not results:
                estado = f" ({state_filter})" if state_filter else ""
                return f"ℹ️ No hay solicitudes de vacaciones{estado}."

            response = f"🏖️ **Solicitudes de Vacaciones** ({len(results)})\n\n"
            if state_filter:
                response += f"_Filtro: {state_filter}_\n\n"

            for leave in results:
                estado = leave.get('estado', '?')
                icon = "✅" if estado == 'approved' else "⏳" if estado == 'pending' else "❌"
                response += f"{icon} **{leave.get('empleado_nombre', 'N/A')}**\n"
                response += f"   {leave.get('tipo', 'N/A')} | {leave.get('inicio')} a {leave.get('fin')} ({leave.get('dias_totales', 0)} días)\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en vacaciones: {str(e)[:150]}")
            return f"⚠️ Error: {str(e)[:80]}"

    def _process_loans_query(self, query: str, user_roles: List[str]) -> str:
        """
        Procesa consulta sobre créditos y préstamos
        """
        logger.info(f"  💰 Procesando query de CRÉDITOS: {query}")

        try:
            state_filter = self._detect_state_filter(query)

            sql = f"""
            SELECT lr.id, u.name as empleado, lr.amount as monto,
                   lr.status as estado, lr.reason as razon, lr.created_at as fecha
            FROM loan_requests lr
            LEFT JOIN users u ON lr.user_id = u.id
            WHERE 1=1
            {f"AND lr.status = '{state_filter}'" if state_filter else ""}
            ORDER BY lr.created_at DESC
            LIMIT 20
            """

            results = self._execute_query(sql)

            if not results:
                estado = f" ({state_filter})" if state_filter else ""
                return f"ℹ️ No hay solicitudes de crédito{estado}."

            response = f"💰 **Solicitudes de Crédito/Adelanto** ({len(results)})\n\n"
            if state_filter:
                response += f"_Filtro: {state_filter}_\n\n"

            for loan in results:
                estado = loan.get('estado', '?')
                icon = "✅" if estado == 'approved' else "⏳" if estado == 'pending' else "❌"
                response += f"{icon} **{loan.get('empleado', 'N/A')}** - ${loan.get('monto', 0)}\n"
                response += f"   {loan.get('razon', 'Sin motivo')} ({loan.get('fecha')})\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en créditos: {str(e)[:150]}")
            return f"⚠️ Error: {str(e)[:80]}"

    def _process_policies_query(self, query: str, user_roles: List[str]) -> str:
        """
        Procesa consulta sobre políticas
        """
        logger.info(f"  📖 Procesando query de POLÍTICAS: {query}")

        try:
            sql = """
            SELECT id, title as titulo, description as descripcion, content as contenido
            FROM policy_guidelines
            WHERE status = 'active'
            ORDER BY title
            LIMIT 20
            """

            results = self._execute_query(sql)

            if not results:
                return "ℹ️ No hay políticas disponibles."

            response = f"📖 **Políticas y Pautas Internas** ({len(results)})\n\n"

            for policy in results:
                response += f"### {policy.get('titulo', 'Sin título')}\n"
                if policy.get('descripcion'):
                    response += f"{policy.get('descripcion')}\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en políticas: {str(e)[:150]}")
            return f"⚠️ Error: {str(e)[:80]}"

    def _process_reminders_query(self, query: str, user_roles: List[str]) -> str:
        """
        Procesa consulta sobre recordatorios administrativos
        """
        logger.info(f"  🔔 Procesando query de RECORDATORIOS: {query}")

        try:
            sql = """
            SELECT id, title as titulo, description as descripcion,
                   assigned_to as asignado_a, status as estado,
                   due_date as fecha_vencimiento
            FROM administrative_reminders
            WHERE status IN ('pending', 'in_progress')
            ORDER BY due_date ASC
            LIMIT 25
            """

            results = self._execute_query(sql)

            if not results:
                return "✅ No hay recordatorios administrativos pendientes en este momento."

            response = f"🔔 **Recordatorios Administrativos Pendientes** ({len(results)})\n\n"

            for reminder in results:
                try:
                    response += f"⏳ **{reminder.get('titulo', 'Sin título')}**\n"
                    if reminder.get('asignado_a'):
                        response += f"   Asignado a: {reminder.get('asignado_a')}\n"
                    if reminder.get('descripcion'):
                        response += f"   {reminder.get('descripcion')}\n"
                    response += f"   Vence: {reminder.get('fecha_vencimiento', 'Sin fecha')}\n\n"
                except Exception as e:
                    logger.warning(f"⚠️ Error procesando recordatorio: {str(e)}")
                    continue

            return response if response.strip() else "ℹ️ No se pudo procesar los recordatorios."

        except Exception as e:
            logger.error(f"❌ Error en recordatorios: {str(e)[:150]}")
            return f"⚠️ Error: {str(e)[:80]}"

    def _extract_search_term(self, query: str, context_keywords: List[str]) -> Optional[str]:
        """
        Extrae término de búsqueda limpio - SOLO EL NOMBRE
        """
        query_lower = query.lower()
        stop_words = {'de', 'del', 'la', 'el', 'los', 'las', 'una', 'un', 'unos', 'unas', 'es', 'son', 'y', 'el', 'la'}

        for keyword in context_keywords:
            pos = query_lower.find(keyword)
            if pos != -1:
                # Extraer todo después de la keyword
                after_keyword = query[pos + len(keyword):].strip()

                # Limpiar puntuación
                for char in ['?', '.', ',', ';', '!', ':']:
                    after_keyword = after_keyword.split(char)[0]

                after_keyword = after_keyword.strip()

                # Remover caracteres especiales pero mantener acentos
                term = ''.join(c for c in after_keyword if c.isalnum() or c.isspace() or ord(c) > 127).strip()

                # Remover stop words del inicio Y del final
                words = term.split()

                # Remover del inicio
                while words and words[0].lower() in stop_words:
                    words.pop(0)

                # Remover del final
                while words and words[-1].lower() in stop_words:
                    words.pop()

                term = ' '.join(words).strip()

                if term and len(term) > 0:
                    logger.info(f"  🔍 Search term extracted: '{term}'")
                    return term

        return None

    def _detect_state_filter(self, query: str) -> Optional[str]:
        """
        Detecta si la query especifica un estado particular
        """
        query_lower = query.lower()

        state_map = {
            'pending': ['pendiente', 'espera', 'por aprobar'],
            'approved': ['aprobada', 'aprobado', 'acepta'],
            'rejected': ['rechazada', 'rechazado', 'denegada'],
            'completed': ['completada', 'completado', 'hecha', 'hecho'],
        }

        for state, keywords in state_map.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return state

        return None

    def get_pending_reminders_for_greeting(self, user_id: int = None) -> dict:
        """
        Genera recordatorios AUTOMÁTICOS desde la BD
        """
        if not self.sql_database:
            return {"count": 0, "reminders": [], "error": "DB no disponible"}

        reminders = []

        try:
            # Vacaciones pendientes
            try:
                result = self._execute_query("SELECT COUNT(*) as total FROM leave_requests WHERE request_status = 'pending'")
                if result and result[0].get('total', 0) > 0:
                    reminders.append({"emoji": "🏖️", "titulo": f"{result[0]['total']} vacaciones pendientes", "tipo": "vacaciones"})
            except Exception as e:
                logger.warning(f"⚠️ No se pudo consultar vacaciones: {str(e)[:100]}")

            # Créditos pendientes (tabla opcional)
            try:
                result = self._execute_query("SELECT COUNT(*) as total FROM loan_requests WHERE status = 'pending'")
                if result and result[0].get('total', 0) > 0:
                    reminders.append({"emoji": "💰", "titulo": f"{result[0]['total']} créditos pendientes", "tipo": "creditos"})
            except Exception as e:
                logger.warning(f"⚠️ Tabla loan_requests no disponible: {str(e)[:100]}")

            # Recordatorios manuales
            try:
                result = self._execute_query("SELECT COUNT(*) as total FROM administrative_reminders WHERE status IN ('pending', 'in_progress')")
                if result and result[0].get('total', 0) > 0:
                    reminders.append({"emoji": "⏰", "titulo": f"{result[0]['total']} recordatorios pendientes", "tipo": "recordatorios"})
            except Exception as e:
                logger.warning(f"⚠️ No se pudo consultar recordatorios: {str(e)[:100]}")

            return {"count": len(reminders), "reminders": reminders[:5], "error": None}

        except Exception as e:
            logger.error(f"❌ Error en recordatorios automáticos: {str(e)[:150]}")
            return {"count": 0, "reminders": [], "error": str(e)[:100]}
