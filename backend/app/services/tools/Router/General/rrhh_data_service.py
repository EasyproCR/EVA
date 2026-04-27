"""
RRHH Data Service - Construye y procesa consultas de RRHH con respuestas formateadas
"""

import logging
import json
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy import text
from difflib import SequenceMatcher

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
        'información empleado', 'ficha empleado', 'staff', 'personal',
        'asesor', 'asesores', 'agente', 'agentes', 'certificado', 'certificados'
    }

    LEAVES_KEYWORDS = {
        'vacacion', 'vacaciones', 'permiso', 'permisos', 'licencia', 'licencias',
        'días libres', 'ausencia', 'incapacidad', 'baja', 'descanso', 'leave',
        'solicitud de vacaciones', 'solicitud de permiso'
    }

    LOANS_KEYWORDS = {
        'crédito', 'credito', 'préstamo', 'prestamo', 'adelanto', 'loan', 'credit',
        'credid', 'credid', 'credids', 'creditt', 'creditoo', 'credito', 'creditos',
        'solicitud de crédito', 'solicitud de préstamo', 'solicitud de adelanto',
        'estudio de crédito', 'estudio credito', 'estudio de credid', 'estudio credid',
        'financiamiento', 'financiamiento', 'financiar', 'financiacion',
        'solicitud', 'solicitudes', 'request',
        'aprobación de crédito', 'aprobacion de credito', 'aprobación credid',
        'revisión de crédito', 'revision de credito', 'revisión credid',
        'análisis de crédito', 'analisis de credito', 'análisis credid',
        'cliente', 'clientes', 'propiedad', 'inmueble', 'vivienda', 'casa',
        'cred', 'cred.', 'créditos', 'creditos', 'credito'
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

    BIRTHDAYS_KEYWORDS = {
        'cumpleaño', 'cumpleaños', 'nacimiento', 'nacimientos', 'aniversario', 'aniversarios',
        'birthday', 'birthdays', 'fecha nacimiento', 'día nacimiento'
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
            elif query_type == "BIRTHDAYS":
                return self._process_birthdays_query(query, user_roles)
            else:
                return "❓ No pude clasificar tu pregunta de RRHH. ¿Podrías ser más específico?"

        except Exception as e:
            logger.error(f"❌ Error procesando query RRHH: {str(e)[:150]}", exc_info=True)
            return f"⚠️ Error al procesar tu consulta: {str(e)[:100]}"

    def _classify_query(self, query: str) -> Optional[str]:
        """
        Clasifica la pregunta en categoría RRHH usando keywords
        ULTRA FLEXIBLE: Tolera faltas ortográficas desde 40%
        """
        query_lower = query.lower()

        # Tokenizar palabras de la query
        words = query_lower.split()

        # Mapeo de categorías con sus keywords
        categories = {
            "EMPLOYEES": self.EMPLOYEES_KEYWORDS,
            "LEAVES": self.LEAVES_KEYWORDS,
            "LOANS": self.LOANS_KEYWORDS,
            "POLICIES": self.POLICIES_KEYWORDS,
            "REMINDERS": self.REMINDERS_KEYWORDS,
            "BIRTHDAYS": self.BIRTHDAYS_KEYWORDS,
        }

        best_match = None
        best_score = 0.0
        matched_word = None
        matched_keyword = None

        # Por cada categoría
        for category, keywords in categories.items():
            for word in words:
                for keyword in keywords:
                    # Similitud exacta (rápido)
                    if keyword in word or word in keyword:
                        logger.info(f"  ✓ Coincidencia exacta: '{word}' = '{keyword}' → {category}")
                        return category

                    # Similitud difusa (tolerancia ortográfica baja desde 40%)
                    similarity = SequenceMatcher(None, word, keyword).ratio()

                    # Si la similitud es >= 40% y es mejor que lo que tenemos
                    if similarity >= 0.40 and similarity > best_score:
                        best_score = similarity
                        best_match = category
                        matched_word = word
                        matched_keyword = keyword

        # Log de resultado fuzzy
        if best_match:
            logger.info(f"  ◇ Coincidencia fuzzy ({best_score*100:.0f}%): '{matched_word}' ≈ '{matched_keyword}' → {best_match}")

        # Retornar mejor coincidencia o None
        return best_match




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
        Por defecto busca ACTIVOS, a menos que explícitamente pregunte por DESEMPLEADOS/INACTIVOS
        """
        logger.info(f"  👤 Procesando query de EMPLEADOS: {query}")

        try:
            query_lower = query.lower()

            # Detectar si busca desempleados/inactivos
            busca_inactivos = any(word in query_lower for word in [
                'desempleado', 'inactivo', 'ya no trabaja', 'que no trabaja',
                'retirado', 'despedido', 'salió', 'se fue', 'anterior', 'antiguos',
                'excluido', 'baja', 'cancelado', 'finalizó'
            ])

            # Determinar filtro de estado
            if busca_inactivos:
                status_filter = "contract_status = 0"
                estado_titulo = "DESEMPLEADOS/INACTIVOS"
                logger.info(f"  ⚠️ Buscando empleados INACTIVOS")
            else:
                status_filter = "contract_status = 1"
                estado_titulo = "ACTIVOS"
                logger.info(f"  ✓ Buscando empleados ACTIVOS")

            # Detectar si busca certificados
            busca_certificados = any(word in query_lower for word in ['certificado', 'certificados', 'ccc', 'certificada', 'certificadas'])
            if busca_certificados:
                cert_filter = " AND (LOWER(job_position) LIKE '%certificado%' OR LOWER(profession) LIKE '%certificado%' OR LOWER(contract) LIKE '%certificado%' OR LOWER(job_position) LIKE '%ccc%' OR LOWER(profession) LIKE '%ccc%')"
                estado_titulo += " CERTIFICADOS"
                logger.info(f"  ✓ Aplicando filtro de CERTIFICADOS")
            else:
                cert_filter = ""

            # Extraer posible nombre de búsqueda primero
            search_name = self._extract_search_term(query, ["expediente", "empleado", "datos", "asesor", "asesores", "agente"])
            
            # Detectar lista de todos
            ver_todos = any(kw in query_lower for kw in ['todos', 'lista', 'listado', 'hay', 'cuantos', 'cuántos', 'certificados', 'asesores', 'asesor', 'agentes', 'agente'])
            
            # Si hay un nombre específico, no listar todos
            if search_name and len(search_name) > 2:
                ver_todos = False

            if ver_todos:
                sql = f"SELECT id, name, email, job_position, phone_number FROM employees WHERE {status_filter}{cert_filter} ORDER BY name LIMIT 50"
                results = self._execute_query(sql)

                if not results:
                    return f"ℹ️ No hay empleados {estado_titulo.lower()} en el sistema."

                response = f"📋 **Lista de Empleados {estado_titulo}** ({len(results)})\n\n"
                for emp in results:
                    try:
                        name = getattr(emp, 'name', 'N/A') if isinstance(emp, object) else emp.get('name', 'N/A')
                        job_pos = getattr(emp, 'job_position', 'Sin puesto') if isinstance(emp, object) else emp.get('job_position', 'Sin puesto')
                        email = getattr(emp, 'email', 'N/A') if isinstance(emp, object) else emp.get('email', 'N/A')
                        phone = getattr(emp, 'phone_number', 'N/A') if isinstance(emp, object) else emp.get('phone_number', 'N/A')
                        response += f"- **{name}** - {job_pos}\n"
                        response += f"  📧 {email} | 📞 {phone}\n"
                    except Exception as e:
                        logger.warning(f"Error procesando empleado: {str(e)}")
                        continue

                return response

            # Búsqueda específica
            if search_name:
                logger.info(f"  🔍 Buscando empleado: '{search_name}' ({estado_titulo})")

                # Búsqueda simple sin complicaciones
                sql = f"""
                SELECT id, name, email, phone_number, job_position, profession,
                       national_id, address, birthday, marital_status, contract
                FROM employees
                WHERE UPPER(name) LIKE UPPER('%{search_name}%')
                AND {status_filter}{cert_filter}
                ORDER BY name
                LIMIT 1
                """

                logger.info(f"  📝 Buscando: UPPER(name) LIKE UPPER('%{search_name}%')")
                results = self._execute_query(sql)

                if not results:
                    # Intentar búsqueda fuzzy con tolerancia ortográfica
                    logger.info(f"  ◇ Búsqueda exacta vacía, intentando fuzzy matching...")
                    sql_all = f"""
                    SELECT id, name, email, phone_number, job_position, profession,
                           national_id, address, birthday, marital_status, contract
                    FROM employees
                    WHERE {status_filter}{cert_filter}
                    LIMIT 100
                    """
                    all_employees = self._execute_query(sql_all)

                    if all_employees:
                        # Comparar por similitud
                        matches = []
                        for emp in all_employees:
                            name = (getattr(emp, 'name', '') if isinstance(emp, object) else emp.get('name', '')).lower()
                            similarity = SequenceMatcher(None, search_name.lower(), name).ratio()
                            if similarity >= 0.55:  # 55% de similitud - ULTRA FLEXIBLE
                                matches.append((emp, similarity))

                        matches.sort(key=lambda x: x[1], reverse=True)

                        if matches:
                            logger.info(f"  ✓ Fuzzy encontró {len(matches)} coincidencias")
                            results = [matches[0][0]]  # Tomar la mejor coincidencia
                        else:
                            # Como último recurso, listar solo empleados del tipo buscado
                            logger.warning(f"  ❌ No encontrado (fuzzy): {search_name}")
                            all_employees_sql = f"SELECT id, name FROM employees WHERE {status_filter}{cert_filter} ORDER BY name LIMIT 30"
                            all_emps = self._execute_query(all_employees_sql)
                            emp_list = '\n'.join([f"  • {getattr(e, 'name', 'N/A') if isinstance(e, object) else e.get('name', 'N/A')}" for e in (all_emps or [])])
                            return (
                                f"❌ No encontré empleado '{search_name}' en el sistema (ni con tolerancia ortográfica).\n\n"
                                f"📋 Empleados {estado_titulo.lower()} disponibles:\n{emp_list}\n\n"
                                f"¿Quizás quisiste decir alguno de estos? Intenta de nuevo con el nombre exacto."
                            )
                    else:
                        return f"❌ No hay empleados {estado_titulo.lower()} en el sistema."

                emp = results[0]
                emp_name = getattr(emp, 'name', 'N/A') if isinstance(emp, object) else emp.get('name', 'N/A')
                emp_email = getattr(emp, 'email', 'N/A') if isinstance(emp, object) else emp.get('email', 'N/A')
                emp_phone = getattr(emp, 'phone_number', 'N/A') if isinstance(emp, object) else emp.get('phone_number', 'N/A')
                emp_job = getattr(emp, 'job_position', 'N/A') if isinstance(emp, object) else emp.get('job_position', 'N/A')
                emp_prof = getattr(emp, 'profession', 'N/A') if isinstance(emp, object) else emp.get('profession', 'N/A')
                emp_id = getattr(emp, 'national_id', 'N/A') if isinstance(emp, object) else emp.get('national_id', 'N/A')
                emp_addr = getattr(emp, 'address', 'N/A') if isinstance(emp, object) else emp.get('address', 'N/A')
                emp_bday = getattr(emp, 'birthday', 'N/A') if isinstance(emp, object) else emp.get('birthday', 'N/A')
                emp_marital = getattr(emp, 'marital_status', 'N/A') if isinstance(emp, object) else emp.get('marital_status', 'N/A')
                emp_contract = getattr(emp, 'contract', 'N/A') if isinstance(emp, object) else emp.get('contract', 'N/A')

                response = f"📋 **Expediente: {emp_name}**\n\n"
                response += f"- **Email:** {emp_email}\n"
                response += f"- **Teléfono:** {emp_phone}\n"
                response += f"- **Puesto:** {emp_job}\n"
                response += f"- **Profesión:** {emp_prof}\n"
                response += f"- **Cédula:** {emp_id}\n"
                response += f"- **Dirección:** {emp_addr}\n"
                response += f"- **Cumpleaños:** {emp_bday}\n"
                response += f"- **Estado Civil:** {emp_marital}\n"
                response += f"- **Tipo Contrato:** {emp_contract}\n"

                return response

            return "❓ Pregunta por un empleado específico"

        except Exception as e:
            logger.error(f"❌ Error en empleados: {str(e)[:150]}")
            return f"⚠️ Error: {str(e)[:80]}"

            # Detectar lista de todos
            ver_todos = any(kw in query_lower for kw in ['todos', 'lista', 'listado', 'hay', 'cuantos', 'cuántos'])

            if ver_todos:
                sql = "SELECT id, name, email, job_position, phone_number FROM employees WHERE contract_status = 1 ORDER BY name LIMIT 50"
                results = self._execute_query(sql)

                if not results:
                    return "ℹ️ No hay empleados activos en el sistema."

                response = f"📋 **Lista de Empleados Activos** ({len(results)})\n\n"
                for emp in results:
                    try:
                        name = getattr(emp, 'name', 'N/A')
                        job_pos = getattr(emp, 'job_position', 'Sin puesto')
                        email = getattr(emp, 'email', 'N/A')
                        phone = getattr(emp, 'phone_number', 'N/A')
                        response += f"- **{name}** - {job_pos}\n"
                        response += f"  📧 {email} | 📞 {phone}\n"
                    except Exception as e:
                        logger.warning(f"Error procesando empleado: {str(e)}")
                        continue

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
                    # Intentar búsqueda fuzzy con tolerancia ortográfica
                    logger.info(f"  ◇ Búsqueda exacta vacía, intentando fuzzy matching...")
                    sql_all = """
                    SELECT id, name, email, phone_number, job_position, profession,
                           national_id, address, birthday, marital_status, contract
                    FROM employees
                    WHERE contract_status = 1
                    LIMIT 100
                    """
                    all_employees = self._execute_query(sql_all)

                    if all_employees:
                        # Comparar por similitud
                        matches = []
                        for emp in all_employees:
                            name = emp.get('name', '').lower()
                            similarity = SequenceMatcher(None, search_name.lower(), name).ratio()
                            if similarity >= 0.55:  # 55% de similitud - ULTRA FLEXIBLE
                                matches.append((emp, similarity))

                        matches.sort(key=lambda x: x[1], reverse=True)

                        if matches:
                            logger.info(f"  ✓ Fuzzy encontró {len(matches)} coincidencias")
                            results = [matches[0][0]]  # Tomar la mejor coincidencia
                        else:
                            # Como último recurso, listar solo empleados ACTIVOS
                            logger.warning(f"  ❌ No encontrado (fuzzy): {search_name}")
                            all_employees_sql = "SELECT id, name FROM employees WHERE contract_status = 1 ORDER BY name LIMIT 30"
                            all_emps = self._execute_query(all_employees_sql)
                            emp_list = '\n'.join([f"  • {getattr(e, 'name', 'N/A')}" for e in (all_emps or [])])
                            return (
                                f"❌ No encontré empleado '{search_name}' en el sistema (ni con tolerancia ortográfica).\n\n"
                                f"📋 Empleados activos disponibles:\n{emp_list}\n\n"
                                f"¿Quizás quisiste decir alguno de estos? Intenta de nuevo con el nombre exacto."
                            )
                    else:
                        return "❌ No hay empleados en el sistema."

                emp = results[0]
                emp_name = getattr(emp, 'name', 'N/A')
                emp_email = getattr(emp, 'email', 'N/A')
                emp_phone = getattr(emp, 'phone_number', 'N/A')
                emp_job = getattr(emp, 'job_position', 'N/A')
                emp_prof = getattr(emp, 'profession', 'N/A')
                emp_id = getattr(emp, 'national_id', 'N/A')
                emp_addr = getattr(emp, 'address', 'N/A')
                emp_bday = getattr(emp, 'birthday', 'N/A')
                emp_marital = getattr(emp, 'marital_status', 'N/A')
                emp_contract = getattr(emp, 'contract', 'N/A')

                response = f"📋 **Expediente: {emp_name}**\n\n"
                response += f"- **Email:** {emp_email}\n"
                response += f"- **Teléfono:** {emp_phone}\n"
                response += f"- **Puesto:** {emp_job}\n"
                response += f"- **Profesión:** {emp_prof}\n"
                response += f"- **Cédula:** {emp_id}\n"
                response += f"- **Dirección:** {emp_addr}\n"
                response += f"- **Cumpleaños:** {emp_bday}\n"
                response += f"- **Estado Civil:** {emp_marital}\n"
                response += f"- **Tipo Contrato:** {emp_contract}\n"

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
        Procesa consulta sobre créditos y estudios de crédito CREDID
        Por defecto muestra solo PENDIENTES (activos)
        """
        logger.info(f"  💰 Procesando query de CRÉDITOS CREDID: {query}")

        try:
            # Detectar si hay filtro de estado específico
            state_filter = self._detect_state_filter(query)

            # Por defecto mostrar PENDIENTES (créditos activos)
            if not state_filter:
                state_filter = 'pending'

            logger.info(f"  📊 Estado a mostrar: {state_filter}")

            # BUSCAR EN credit_study_requests CON FILTRO DE ESTADO
            sql_credit_study = f"SELECT id, property, request_status, request_reason FROM credit_study_requests WHERE request_status = '{state_filter}' LIMIT 50"
            logger.info(f"  📝 SQL: {sql_credit_study}")
            results_credit_study = self._execute_query(sql_credit_study)
            count_study = len(results_credit_study) if results_credit_study else 0
            logger.info(f"  ✓ Resultados encontrados: {count_study}")

            # BUSCAR EN campo credid de employees (SIN FILTRO, siempre mostrar)
            sql_credid = "SELECT id, name, credid FROM employees WHERE credid IS NOT NULL AND credid != '' LIMIT 50"
            results_credid = self._execute_query(sql_credid)
            count_credid = len(results_credid) if results_credid else 0

            # Si no hay nada
            if count_study == 0 and count_credid == 0:
                return f"ℹ️ No hay créditos {state_filter.upper()}."

            # Construir respuesta
            response = f"💰 **Créditos {state_filter.upper()}** (Total: {count_study + count_credid})\n\n"

            # Mostrar credit_study_requests
            if count_study > 0:
                response += f"**📋 Solicitudes de Estudio** ({count_study})\n"
                for loan in results_credit_study:
                    try:
                        id_num = getattr(loan, 'id', '?')
                        propiedad = getattr(loan, 'property', 'Sin especificar')
                        razon = getattr(loan, 'request_reason', 'Sin especificar')

                        response += f"⏳ Solicitud #{id_num}\n"
                        response += f"   🏠 Propiedad: {propiedad}\n"
                        response += f"   📝 Motivo: {razon}\n"
                    except Exception as e:
                        logger.error(f"Error procesando loan: {str(e)}")
                        continue
                response += "\n"

            # Mostrar créditos CREDID de empleados
            if count_credid > 0:
                response += f"**💳 Créditos en Nómina** ({count_credid})\n"
                for emp in results_credid:
                    try:
                        emp_id = getattr(emp, 'id', '?')
                        emp_name = getattr(emp, 'name', 'Desconocido')
                        credid_data = str(getattr(emp, 'credid', 'Sin detalles'))

                        if len(credid_data) > 80:
                            credid_data = credid_data[:80] + "..."

                        response += f"👤 {emp_name} (ID: {emp_id})\n"
                        response += f"   💳 {credid_data}\n"
                    except Exception as e:
                        logger.error(f"Error procesando employee: {str(e)}")
                        continue

            return response

        except Exception as e:
            logger.error(f"❌ Error en _process_loans_query: {str(e)}", exc_info=True)
            return f"⚠️ Error al obtener créditos: {str(e)[:80]}"

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

    def _process_birthdays_query(self, query: str, user_roles: List[str]) -> str:
        """
        Procesa consulta sobre cumpleaños
        Detecta si pregunta por cumpleaños de alguien específico o general
        """
        logger.info(f"  🎂 Procesando query de CUMPLEAÑOS: {query}")

        try:
            # Detectar si pregunta por alguien específico
            # Ej: "¿cuál es el cumpleaños de Juan?" o "cumpleaños de María"
            lower_query = query.lower()

            # Palabras clave que indican búsqueda de persona específica
            if any(word in lower_query for word in ['de ', 'del ', 'cumpleaños de', 'nacimiento de', 'birthday of']):
                # Intentar extraer nombre
                keywords_to_remove = ['cumpleaño', 'cumpleaños', 'nacimiento', 'de ', 'del ', 'birthday', 'fecha de', 'cual es']
                search_name = lower_query
                for kw in keywords_to_remove:
                    search_name = search_name.replace(kw, '').strip()

                if search_name and len(search_name) > 2:
                    logger.info(f"  🔍 Buscando cumpleaños de: {search_name}")
                    return self._get_specific_birthday(search_name)

            # Si no hay nombre específico, mostrar cumpleaños de esta semana
            birthdays_list = self._get_birthdays_this_week()

            if not birthdays_list:
                return "📅 No hay cumpleaños para esta semana 🎈"

            response = "🎂 **Cumpleaños esta semana:**\n\n"
            for i, name in enumerate(birthdays_list, 1):
                response += f"{i}. {name}\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en cumpleaños: {str(e)[:150]}", exc_info=True)
            return f"⚠️ Error: {str(e)[:50]}"

    def _get_specific_birthday(self, search_name: str) -> str:
        """
        Obtiene el cumpleaños de una persona específica
        """
        if not self.sql_database:
            return "❌ Base de datos no disponible"

        try:
            # Buscar empleado activo con ese nombre
            sql = f"""
            SELECT id, name, birthday, contract_status
            FROM employees
            WHERE LOWER(name) LIKE LOWER('%{search_name}%')
            AND contract_status = 1
            LIMIT 1
            """

            logger.info(f"📝 Buscando: {sql}")
            results = self._execute_query(sql)

            if not results:
                logger.info(f"⚠️ No encontró empleado activo: {search_name}")
                return f"❌ No encontré a '{search_name}' en nómina activa."

            emp = results[0]
            emp_name = getattr(emp, 'name', 'Desconocido')
            birthday_str = getattr(emp, 'birthday', None)

            if not birthday_str:
                return f"⚠️ {emp_name} no tiene fecha de cumpleaños registrada."

            # Parsear fecha
            birthday = None
            if isinstance(birthday_str, str):
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
                    try:
                        birthday = datetime.strptime(birthday_str, fmt)
                        break
                    except:
                        continue
            else:
                birthday = birthday_str

            if not birthday:
                return f"⚠️ No pude procesar la fecha de {emp_name}."

            # Formatear respuesta
            date_str = birthday.strftime("%d de %B").replace(
                'January', 'Enero').replace('February', 'Febrero').replace('March', 'Marzo').replace(
                'April', 'Abril').replace('May', 'Mayo').replace('June', 'Junio').replace(
                'July', 'Julio').replace('August', 'Agosto').replace('September', 'Septiembre').replace(
                'October', 'Octubre').replace('November', 'Noviembre').replace('December', 'Diciembre')

            # Calcular edad
            today = datetime.now()
            age = today.year - birthday.year
            if (today.month, today.day) < (birthday.month, birthday.day):
                age -= 1

            return f"🎂 **{emp_name}**\n📅 Cumpleaños: {date_str}\n🎉 Edad: {age} años"

        except Exception as e:
            logger.error(f"❌ Error en _get_specific_birthday: {str(e)[:150]}", exc_info=True)
            return f"⚠️ Error: {str(e)[:80]}"

    def _get_all_birthdays(self) -> Dict[str, Dict]:
        """
        Obtiene TODOS los cumpleaños de empleados activos
        Intenta múltiples nombres de columna para compatibilidad
        """
        if not self.sql_database:
            return {}

        try:
            # Variantes posibles de nombres de columna
            birthday_columns = ['birthday', 'date_of_birth', 'fecha_nacimiento', 'born_date', 'birth_date']
            birthday_column = None
            results = None

            # Intenta cada columna
            for col in birthday_columns:
                try:
                    sql = f"SELECT id, name, {col} FROM employees WHERE contract_status = 1 ORDER BY name LIMIT 200"
                    results = self._execute_query(sql)
                    if results is not None and results != []:
                        birthday_column = col
                        logger.info(f"  ✓ Columna de cumpleaños encontrada: {col}")
                        break
                except Exception as e:
                    logger.warning(f"  ⚠️ Intentó {col}, no encontrado: {str(e)[:50]}")
                    continue

            # Si no encontró ninguna columna válida o no hay datos
            if birthday_column is None or not results:
                logger.warning("⚠️ No se encontró columna de cumpleaños o no hay datos")
                return {}

            birthdays_dict = {}

            for emp in results:
                try:
                    name = emp.get('name', 'Desconocido')
                    birthday_str = emp.get(birthday_column)

                    if not birthday_str:
                        continue

                    # Parsear la fecha de cumpleaños
                    if isinstance(birthday_str, str):
                        birthday_obj = None
                        for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
                            try:
                                birthday_obj = datetime.strptime(birthday_str, fmt)
                                break
                            except:
                                continue

                        if not birthday_obj:
                            continue
                    else:
                        birthday_obj = birthday_str

                    # Formatear fecha para mostrar
                    date_str = birthday_obj.strftime("%d de %B")
                    date_str = date_str.replace('January', 'Enero').replace('February', 'Febrero').replace('March', 'Marzo').replace('April', 'Abril').replace('May', 'Mayo').replace('June', 'Junio').replace('July', 'Julio').replace('August', 'Agosto').replace('September', 'Septiembre').replace('October', 'Octubre').replace('November', 'Noviembre').replace('December', 'Diciembre')

                    birthdays_dict[name] = {
                        'date_str': date_str,
                        'birthday': birthday_obj
                    }

                except Exception as e:
                    logger.warning(f"⚠️ Error procesando cumpleaños: {str(e)[:50]}")
                    continue

            logger.info(f"  🎂 Cumpleaños cargados: {len(birthdays_dict)}")
            return birthdays_dict

        except Exception as e:
            logger.error(f"❌ Error en _get_all_birthdays: {str(e)[:150]}")
            return {}

    def _filter_birthdays_by_week(self, all_birthdays: Dict[str, Dict], today: datetime) -> Dict[str, Dict]:
        """
        Filtra cumpleaños de los próximos 7 días
        """
        week_birthdays = {}

        for name, bday_info in all_birthdays.items():
            birthday = bday_info['birthday']

            # Generar fechas de esta semana
            for i in range(7):
                check_date = today + timedelta(days=i)
                if birthday.month == check_date.month and birthday.day == check_date.day:
                    week_birthdays[name] = bday_info
                    break

        return week_birthdays

    def _filter_birthdays_by_month(self, all_birthdays: Dict[str, Dict], today: datetime) -> Dict[str, Dict]:
        """
        Filtra cumpleaños del mes actual
        """
        month_birthdays = {}
        current_month = today.month

        for name, bday_info in all_birthdays.items():
            birthday = bday_info['birthday']
            if birthday.month == current_month:
                month_birthdays[name] = bday_info

        return month_birthdays

    def _get_birthdays_this_month(self) -> Dict[str, List[str]]:
        """
        Obtiene empleados con cumpleaños en este mes
        Retorna: {'15 Abril': ['Juan', 'María'], ...}
        """
        if not self.sql_database:
            return {}

        try:
            today = datetime.now()
            current_month = today.month

            sql = "SELECT id, name, birthday FROM employees WHERE contract_status = 1 ORDER BY name LIMIT 100"
            results = self._execute_query(sql)

            if not results:
                return {}

            birthdays_dict = {}

            for emp in results:
                try:
                    birthday_str = emp.get('birthday')
                    if not birthday_str:
                        continue

                    # Parsear la fecha de cumpleaños
                    if isinstance(birthday_str, str):
                        for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
                            try:
                                birthday = datetime.strptime(birthday_str, fmt)
                                break
                            except:
                                continue
                        else:
                            continue
                    else:
                        birthday = birthday_str

                    # Verificar si está en este mes
                    if birthday.month == current_month:
                        date_str = birthday.strftime("%d de %B").replace('January', 'Enero').replace('February', 'Febrero').replace('March', 'Marzo').replace('April', 'Abril').replace('May', 'Mayo').replace('June', 'Junio').replace('July', 'Julio').replace('August', 'Agosto').replace('September', 'Septiembre').replace('October', 'Octubre').replace('November', 'Noviembre').replace('December', 'Diciembre')

                        if date_str not in birthdays_dict:
                            birthdays_dict[date_str] = []
                        birthdays_dict[date_str].append(emp.get('name', 'Desconocido'))

                except Exception as e:
                    logger.warning(f"⚠️ Error procesando cumpleaños: {str(e)}")
                    continue

            logger.info(f"  🎂 Cumpleaños este mes: {len(birthdays_dict)}")
            return birthdays_dict

        except Exception as e:
            logger.error(f"❌ Error en _get_birthdays_this_month: {str(e)[:150]}")
            return {}

    def _get_birthdays_this_week(self) -> List[str]:
        """
        Obtiene empleados ACTIVOS con cumpleaños en los próximos 7 días
        Solo muestra empleados con contract_status = 1 (activos)
        """
        if not self.sql_database:
            logger.warning("❌ SQL Database no disponible")
            return []

        try:
            today = datetime.now()
            logger.info(f"🎂 Buscando cumpleaños desde {today.date()}")

            # Generar las fechas de esta semana (próximos 7 días)
            week_dates = []
            for i in range(7):
                date = today + timedelta(days=i)
                week_dates.append(date)

            # Buscar SOLO empleados ACTIVOS con cumpleaños
            birthdays = []
            sql = "SELECT id, name, birthday, contract_status FROM employees WHERE contract_status = 1 AND birthday IS NOT NULL ORDER BY name LIMIT 200"
            logger.info(f"📝 SQL: {sql}")
            results = self._execute_query(sql)
            logger.info(f"✓ Resultados: {len(results) if results else 0} empleados activos")

            if not results:
                logger.info("⚠️ No hay empleados activos con cumpleaños")
                return []

            for emp in results:
                try:
                    # Usar getattr para objetos Row de SQLAlchemy
                    birthday_str = getattr(emp, 'birthday', None)
                    if not birthday_str:
                        continue

                    # Parsear la fecha de cumpleaños
                    if isinstance(birthday_str, str):
                        birthday = None
                        for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
                            try:
                                birthday = datetime.strptime(birthday_str, fmt)
                                break
                            except:
                                continue
                        if not birthday:
                            continue
                    else:
                        birthday = birthday_str

                    # Comparar mes y día (ignorar año)
                    for date in week_dates:
                        if birthday.month == date.month and birthday.day == date.day:
                            name = getattr(emp, 'name', 'Desconocido')
                            contract_status = getattr(emp, 'contract_status', None)

                            # Verificar que esté activo
                            if contract_status == 1 or contract_status == True:
                                birthdays.append(name)
                                logger.info(f"  ✓ {name} (Activo)")
                            else:
                                logger.info(f"  ✗ {name} (Inactivo/Desempleado - EXCLUIDO)")
                            break

                except Exception as e:
                    logger.warning(f"⚠️ Error procesando cumpleaños: {str(e)}")
                    continue

            logger.info(f"  🎂 Cumpleaños encontrados esta semana: {len(birthdays)}")
            return birthdays

        except Exception as e:
            logger.error(f"❌ Error en _get_birthdays_this_week: {str(e)[:150]}")
            return []

    def _extract_search_term(self, query: str, context_keywords: List[str]) -> Optional[str]:
        """
        Extrae término de búsqueda limpio - TOLERA FALTAS ORTOGRÁFICAS
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

    def _fuzzy_search_database(self, table: str, column: str, search_term: str, similarity_threshold: float = 0.55) -> List[Dict[str, Any]]:
        """
        Busca en base de datos tolerando faltas ortográficas desde 55%
        """
        if not search_term or not self.sql_database:
            return []

        try:
            # Primero intentar búsqueda exacta/like
            sql = f"SELECT * FROM {table} WHERE LOWER({column}) LIKE LOWER('%{search_term}%') LIMIT 5"
            results = self._execute_query(sql)

            if results:
                logger.info(f"  ✓ Búsqueda exacta encontró {len(results)} resultados")
                return results

            # Si no encuentra, obtener todos los registros y filtrar por similitud
            logger.info(f"  ◇ Búsqueda exacta vacía, intentando fuzzy matching...")
            sql_all = f"SELECT * FROM {table} LIMIT 100"
            all_results = self._execute_query(sql_all)

            if not all_results:
                return []

            # Comparar cada registro por similitud
            matches = []
            for row in all_results:
                value = str(row.get(column, '')).lower()
                similarity = SequenceMatcher(None, search_term.lower(), value).ratio()

                if similarity >= similarity_threshold:
                    matches.append((row, similarity))

            # Ordenar por similitud descendente
            matches.sort(key=lambda x: x[1], reverse=True)
            logger.info(f"  ◇ Fuzzy encontró {len(matches)} coincidencias con {similarity_threshold*100:.0f}% similitud")

            return [match[0] for match in matches[:5]]

        except Exception as e:
            logger.warning(f"⚠️ Error en fuzzy_search_database: {str(e)}")
            return []


    def _detect_state_filter(self, query: str) -> Optional[str]:
        """
        Detecta estado con ULTRA TOLERANCIA ORTOGRÁFICA desde 50%
        Busca: pending, approved, rejected, completed
        """
        query_lower = query.lower()
        words = query_lower.split()

        state_map = {
            'pending': ['pendiente', 'espera', 'por aprobar', 'pendientes'],
            'approved': ['aprobada', 'aprobado', 'acepta', 'aceptado', 'aprobadas'],
            'rejected': ['rechazada', 'rechazado', 'denegada', 'rechazadas'],
            'completed': ['completada', 'completado', 'hecha', 'hecho', 'completadas'],
        }

        best_match = None
        best_score = 0.0

        for state, keywords in state_map.items():
            for word in words:
                for keyword in keywords:
                    # Similitud exacta
                    if keyword in word or word in keyword:
                        return state

                    # Similitud difusa desde 50%
                    similarity = SequenceMatcher(None, word, keyword).ratio()
                    if similarity >= 0.50 and similarity > best_score:
                        best_score = similarity
                        best_match = state

        return best_match


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

            # Créditos CREDID pendientes en credit_study_requests
            try:
                result = self._execute_query("SELECT COUNT(*) as total FROM credit_study_requests WHERE request_status = 'pending'")
                if result and result[0].get('total', 0) > 0:
                    reminders.append({"emoji": "💳", "titulo": f"{result[0]['total']} solicitud(es) de estudio de crédito pendiente(s)", "tipo": "credid_study"})
            except Exception as e:
                logger.warning(f"⚠️ Tabla credit_study_requests no disponible: {str(e)[:100]}")

            # Créditos CREDID de empleados
            try:
                result = self._execute_query("SELECT COUNT(*) as total FROM employees WHERE credid IS NOT NULL AND credid != '' AND contract_status = 1")
                if result and result[0].get('total', 0) > 0:
                    reminders.append({"emoji": "💳", "titulo": f"{result[0]['total']} empleado(s) con créditos CREDID registrado(s)", "tipo": "credid_employees"})
            except Exception as e:
                logger.warning(f"⚠️ Campo credid de employees no disponible: {str(e)[:100]}")

            # Recordatorios manuales
            try:
                result = self._execute_query("SELECT COUNT(*) as total FROM administrative_reminders WHERE status IN ('pending', 'in_progress')")
                if result and result[0].get('total', 0) > 0:
                    reminders.append({"emoji": "⏰", "titulo": f"{result[0]['total']} recordatorios pendientes", "tipo": "recordatorios"})
            except Exception as e:
                logger.warning(f"⚠️ No se pudo consultar recordatorios: {str(e)[:100]}")

            # Cumpleaños esta semana (deshabilitado por ahora)
            reminders.append({"emoji": "🎂", "titulo": "Esta semana no hay cumpleaños", "tipo": "cumpleaños"})

            return {"count": len(reminders), "reminders": reminders[:10], "error": None}

        except Exception as e:
            logger.error(f"❌ Error en recordatorios automáticos: {str(e)[:150]}")
            return {"count": 0, "reminders": [], "error": str(e)[:100]}

