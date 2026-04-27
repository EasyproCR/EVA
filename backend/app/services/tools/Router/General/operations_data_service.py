"""
Operations Data Service - Procesa consultas de citas y recordatorios de operaciones
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from sqlalchemy import text
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class OperationsDataService:
    """
    Servicio para procesar consultas de Operaciones:
    - Clasifica preguntas sobre citas
    - Construye queries SQL contra customer_reminders
    - Formatea respuestas legibles
    """

    # Keywords por categoría
    APPOINTMENTS_KEYWORDS = {
        'cita', 'citas', 'appointment', 'appointments', 'reunión', 'reuniones',
        'meeting', 'meetings', 'próximo', 'próxima', 'pendiente', 'pendientes',
        'agendado', 'agendada', 'programado', 'programada', 'scheduled'
    }

    CUSTOMER_KEYWORDS = {
        'cliente', 'clientes', 'customer', 'customers', 'empresa', 'empresas',
        'contact', 'contacto', 'contactos', 'person', 'persona', 'personas'
    }

    PROPERTY_KEYWORDS = {
        'propiedad', 'propiedades', 'property', 'properties', 'finca', 'fincas',
        'terreno', 'terrenos', 'tierra', 'lote', 'lotes', 'inmueble', 'inmuebles',
        'tierra', 'suelo', 'tipo de suelo', 'soil type', 'ground', 'land'
    }

    def __init__(self, sql_database=None):
        """
        Args:
            sql_database: SQLDatabase instance from LlamaIndex
        """
        self.sql_database = sql_database
        logger.info("✓ OperationsDataService inicializado")

    def process_query(self, query: str, user_id: int) -> str:
        """
        Procesa una consulta de operaciones/citas y retorna respuesta formateada

        Args:
            query: Pregunta del usuario
            user_id: ID del usuario (para filtrar sus citas)

        Returns:
            Respuesta formateada en markdown
        """
        if not self.sql_database:
            logger.error("❌ SQL Database no configurada en OperationsDataService")
            return "⚠️ Servicio de operaciones no disponible temporalmente. Por favor, intenta más tarde."

        if not user_id:
            logger.error("❌ User ID requerido para procesar citas")
            return "⚠️ No pudimos identificar tu usuario. Por favor, intenta de nuevo."

        try:
            query_type = self._classify_query(query)
            logger.info(f"  📁 Tipo de consulta: {query_type}")

            if query_type == "APPOINTMENTS_PENDING":
                return self._process_pending_appointments(query, user_id)
            elif query_type == "APPOINTMENTS_CUSTOMER":
                return self._process_customer_appointments(query, user_id)
            elif query_type == "PROPERTY_INFO":
                return self._process_property_info(query)
            else:
                return "❓ No pude entender tu pregunta sobre citas. ¿Podrías ser más específico?"

        except Exception as e:
            logger.error(f"❌ Error procesando query de operaciones: {str(e)[:150]}", exc_info=True)
            return f"⚠️ Error al procesar tu consulta: {str(e)[:100]}"

    def _classify_query(self, query: str) -> Optional[str]:
        """
        Clasifica la pregunta en categoría de operaciones
        """
        query_lower = query.lower()
        words = query_lower.split()

        # Detectar si es pregunta sobre propiedad/suelo
        has_property_keyword = any(word in query_lower for word in self.PROPERTY_KEYWORDS)
        if has_property_keyword:
            logger.info(f"  🏠 Detectada pregunta sobre propiedad")
            return "PROPERTY_INFO"

        # Detectar si es pregunta sobre citas pendientes
        has_appointment_keyword = any(word in query_lower for word in self.APPOINTMENTS_KEYWORDS)
        has_pending_keyword = any(word in query_lower for word in [
            'pendiente', 'pendientes', 'tengo', 'próximo', 'próxima', 'upcoming'
        ])

        if has_appointment_keyword:
            # Buscar si menciona cliente específico
            for word in words:
                for customer_kw in self.CUSTOMER_KEYWORDS:
                    similarity = SequenceMatcher(None, word, customer_kw).ratio()
                    if similarity >= 0.8 or word == customer_kw:
                        logger.info(f"  ◇ Detectado cliente en query: {word}")
                        return "APPOINTMENTS_CUSTOMER"

            # Si no menciona cliente, es pregunta de pendientes
            if has_pending_keyword:
                logger.info(f"  ◇ Detectada pregunta de citas pendientes")
                return "APPOINTMENTS_PENDING"

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

    def _process_pending_appointments(self, query: str, user_id: int) -> str:
        """
        Procesa consulta sobre citas pendientes del usuario
        """
        logger.info(f"  📅 Procesando citas pendientes para user_id: {user_id}")

        try:
            # Obtener citas pendientes para este usuario
            sql = """
            SELECT
                cr.id,
                cr.reminder_date,
                cr.description,
                cr.status,
                COALESCE(c.full_name, 'Cliente sin asignar') as customer_name,
                COALESCE(c.email, '') as customer_email
            FROM customer_reminders cr
            LEFT JOIN customers c ON cr.customer_id = c.id
            WHERE cr.user_id = {user_id}
            AND cr.reminder_type = 'appointment'
            AND cr.status IN ('pending', 'in_progress')
            AND cr.reminder_date >= CURDATE()
            ORDER BY cr.reminder_date ASC
            LIMIT 20
            """.format(user_id=user_id)

            results = self._execute_query(sql)

            if not results:
                logger.info(f"  ✅ No hay citas pendientes")
                return "✅ No tienes citas pendientes."

            logger.info(f"  ✓ Se encontraron {len(results)} citas pendientes")

            # Formatear respuesta
            response = f"📅 **Citas Pendientes** ({len(results)})\n\n"

            for idx, appt in enumerate(results, 1):
                try:
                    customer_name = appt.get('customer_name', 'Cliente sin asignar')
                    reminder_date = appt.get('reminder_date')
                    description = appt.get('description', '')
                    status = appt.get('status', 'pendiente')

                    # Formatear fecha
                    if isinstance(reminder_date, str):
                        try:
                            date_obj = datetime.strptime(reminder_date, '%Y-%m-%d')
                            date_formatted = date_obj.strftime('%d/%m/%Y')
                        except:
                            date_formatted = reminder_date
                    else:
                        date_formatted = str(reminder_date)

                    # Emoji de estado
                    status_emoji = "⏳" if status == "pending" else "⚙️"

                    response += f"{idx}. **{customer_name}**\n"
                    response += f"   {status_emoji} **Fecha:** {date_formatted}\n"
                    if description:
                        response += f"   📝 {description}\n"
                    response += "\n"

                except Exception as e:
                    logger.warning(f"Error formateando cita: {str(e)}")
                    continue

            return response

        except Exception as e:
            logger.error(f"❌ Error procesando citas pendientes: {str(e)}", exc_info=True)
            return f"⚠️ Error al obtener tus citas: {str(e)[:100]}"

    def _process_customer_appointments(self, query: str, user_id: int) -> str:
        """
        Procesa consulta sobre citas con cliente específico
        """
        logger.info(f"  🤝 Procesando citas con cliente específico")

        try:
            # Extraer nombre de cliente
            customer_name = self._extract_customer_name(query)

            if not customer_name:
                logger.info(f"  ⚠️ No se pudo extraer nombre de cliente")
                return "Por favor, especifica el nombre del cliente (ej: 'citas con Juan')"

            logger.info(f"  🔍 Buscando citas con: '{customer_name}'")

            # Buscar citas con este cliente
            sql = """
            SELECT
                cr.id,
                cr.reminder_date,
                cr.description,
                cr.status,
                COALESCE(c.full_name, 'Cliente sin asignar') as customer_name,
                COALESCE(c.email, '') as customer_email
            FROM customer_reminders cr
            LEFT JOIN customers c ON cr.customer_id = c.id
            WHERE cr.user_id = {user_id}
            AND cr.reminder_type = 'appointment'
            AND LOWER(COALESCE(c.full_name, '')) LIKE LOWER('%{search_term}%')
            ORDER BY cr.reminder_date ASC
            LIMIT 20
            """.format(user_id=user_id, search_term=customer_name)

            results = self._execute_query(sql)

            if not results:
                logger.info(f"  ℹ️ No hay citas con {customer_name}")
                return f"ℹ️ No tienes citas registradas con '{customer_name}'."

            logger.info(f"  ✓ Se encontraron {len(results)} citas con {customer_name}")

            # Formatear respuesta
            response = f"📅 **Citas con {customer_name}** ({len(results)})\n\n"

            for idx, appt in enumerate(results, 1):
                try:
                    reminder_date = appt.get('reminder_date')
                    description = appt.get('description', '')
                    status = appt.get('status', 'pendiente')

                    # Formatear fecha
                    if isinstance(reminder_date, str):
                        try:
                            date_obj = datetime.strptime(reminder_date, '%Y-%m-%d')
                            date_formatted = date_obj.strftime('%d/%m/%Y')
                        except:
                            date_formatted = reminder_date
                    else:
                        date_formatted = str(reminder_date)

                    # Emoji de estado
                    status_emoji = "⏳" if status == "pending" else "✅" if status == "completed" else "⚙️"

                    response += f"{idx}. **{date_formatted}** {status_emoji}\n"
                    if description:
                        response += f"   📝 {description}\n"
                    response += "\n"

                except Exception as e:
                    logger.warning(f"Error formateando cita: {str(e)}")
                    continue

            return response

        except Exception as e:
            logger.error(f"❌ Error procesando citas con cliente: {str(e)}", exc_info=True)
            return f"⚠️ Error al buscar citas: {str(e)[:100]}"

    def _extract_customer_name(self, query: str) -> Optional[str]:
        """
        Extrae nombre de cliente de la query
        Busca después de keywords como 'con', 'de', 'para'
        """
        query_lower = query.lower()

        # Palabras que preceden al nombre del cliente
        preceding_words = ['con ', 'de ', 'para ', 'cliente ', 'empresa ']

        for preceding in preceding_words:
            if preceding in query_lower:
                # Obtener texto después del keyword
                parts = query_lower.split(preceding)
                if len(parts) > 1:
                    # Tomar el resto después del keyword
                    after_keyword = parts[-1].strip()
                    # Remover palabras vacías al final
                    words = after_keyword.split()
                    if words:
                        # Retornar las primeras 1-2 palabras como nombre
                        customer_name = ' '.join(words[:2])
                        # Limpiar caracteres especiales
                        customer_name = customer_name.rstrip('?!.,:;')
                        if customer_name and len(customer_name) > 1:
                            return customer_name

        return None

    def get_pending_reminders_for_greeting(self, user_id: int) -> dict:
        """
        Obtiene citas pendientes del usuario para mostrar en el saludo inicial.
        Usado cuando Alejandra abre EVA.

        Args:
            user_id: ID del usuario autenticado

        Returns:
            dict con {count, reminders} donde cada reminder tiene emoji, titulo, fecha_vencimiento
        """
        if not user_id or not self.sql_database:
            return {"count": 0, "reminders": []}

        try:
            sql = """
            SELECT
                cr.id,
                cr.reminder_date,
                cr.description,
                cr.status,
                COALESCE(c.full_name, 'Cliente sin asignar') as customer_name
            FROM customer_reminders cr
            LEFT JOIN customers c ON cr.customer_id = c.id
            WHERE cr.user_id = {user_id}
            AND cr.reminder_type = 'appointment'
            AND cr.status IN ('pending', 'in_progress')
            AND cr.reminder_date >= CURDATE()
            ORDER BY cr.reminder_date ASC
            LIMIT 10
            """.format(user_id=user_id)

            results = self._execute_query(sql)

            if not results:
                return {"count": 0, "reminders": []}

            reminders = []
            for appt in results:
                try:
                    customer_name = appt.get('customer_name', 'Cliente sin asignar')
                    reminder_date = appt.get('reminder_date')

                    # Formatear fecha
                    if isinstance(reminder_date, str):
                        try:
                            date_obj = datetime.strptime(reminder_date, '%Y-%m-%d')
                            date_formatted = date_obj.strftime('%d/%m/%Y')
                        except:
                            date_formatted = str(reminder_date)
                    else:
                        date_formatted = str(reminder_date)

                    reminders.append({
                        'emoji': '📅',
                        'titulo': f"Cita con {customer_name}",
                        'fecha_vencimiento': date_formatted,
                        'accion': 'Revisa los detalles en Operaciones'
                    })
                except Exception as e:
                    logger.warning(f"Error procesando recordatorio: {str(e)}")
                    continue

            return {
                "count": len(reminders),
                "reminders": reminders
            }

        except Exception as e:
            logger.error(f"❌ Error obteniendo recordatorios para saludo: {str(e)}", exc_info=True)
            return {"count": 0, "reminders": []}

    def _extract_property_identifier(self, query: str) -> Optional[tuple]:
        """
        Extrae nombre o link de propiedad de la query
        Retorna: (tipo, valor) donde tipo es 'name', 'link' o None
        """
        import re

        # Buscar URLs en la query
        urls = re.findall(r'https?://\S+', query)
        if urls:
            logger.info(f"  🔗 URL encontrada: {urls[0]}")
            return ('link', urls[0])

        # Buscar nombre entre comillas o después de palabras clave
        name_patterns = [
            r'["\']([^"\']+)["\']',  # Entre comillas
            r'(?:de|del|sobre|llamada|propiedad)\s+([^?¿]+)',  # Después de keyword
        ]

        for pattern in name_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                name = match.group(1).strip().rstrip('?!.,;')
                if len(name) > 2:
                    logger.info(f"  📝 Nombre extraído: {name}")
                    return ('name', name)

        return None

    def _process_property_info(self, query: str) -> str:
        """
        Busca información de una propiedad por nombre o link
        Retorna: Información completa incluyendo tipo_suelo
        """
        if not self.sql_database:
            return "⚠️ Servicio de propiedades no disponible."

        try:
            identifier = self._extract_property_identifier(query)

            if not identifier:
                return "Por favor, proporciona el nombre de la propiedad o su enlace.\nEjemplo: '¿Cuál es el tipo de suelo de la propiedad X?'"

            id_type, id_value = identifier

            if id_type == 'link':
                # Buscar por URL (búsqueda parcial)
                sql = """
                SELECT
                    id,
                    name,
                    finca_number,
                    address,
                    status,
                    service_type,
                    soil_type,
                    monthly_amount,
                    sale_amount,
                    details,
                    created_at
                FROM third_party_properties
                WHERE link LIKE :search_term OR property_url LIKE :search_term
                LIMIT 1
                """
                results = self._execute_query(sql, {'search_term': f"%{id_value}%"})
            else:
                # Buscar por nombre
                sql = """
                SELECT
                    id,
                    name,
                    finca_number,
                    address,
                    status,
                    service_type,
                    soil_type,
                    monthly_amount,
                    sale_amount,
                    details,
                    created_at
                FROM third_party_properties
                WHERE LOWER(name) LIKE LOWER(:search_term)
                LIMIT 1
                """
                results = self._execute_query(sql, {'search_term': f"%{id_value}%"})

            if not results:
                return f"❌ No encontré información de la propiedad '{id_value}'."

            prop = results[0]

            # Construir respuesta formateada
            response = f"🏠 **INFORMACIÓN DE PROPIEDAD**\n\n"
            response += f"**Nombre:** {prop.get('name', 'N/A')}\n"
            response += f"**Número de Finca:** {prop.get('finca_number', 'N/A')}\n"
            response += f"**Dirección:** {prop.get('address', 'N/A')}\n"
            response += f"**Estado:** {prop.get('status', 'N/A')}\n"
            response += f"**Tipo de Servicio:** {prop.get('service_type', 'N/A')}\n"

            # Tipo de suelo - DESTACADO
            soil_type = prop.get('soil_type')
            if soil_type:
                response += f"\n🌍 **TIPO DE SUELO:** {soil_type}\n"
            else:
                response += f"\n🌍 **TIPO DE SUELO:** ❌ No hay tipo de suelo registrado\n"

            # Información económica si existe
            monthly = prop.get('monthly_amount')
            sale = prop.get('sale_amount')
            if monthly or sale:
                response += f"\n💰 **INFORMACIÓN ECONÓMICA:**\n"
                if monthly:
                    response += f"   • Monto Mensual: ${monthly:,.2f}\n"
                if sale:
                    response += f"   • Monto de Venta: ${sale:,.2f}\n"

            # Detalles adicionales
            details = prop.get('details')
            if details:
                response += f"\n📋 **DETALLES:** {details}\n"

            response += f"\n📅 **Registrada:** {prop.get('created_at', 'N/A')}\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error obteniendo info de propiedad: {str(e)}", exc_info=True)
            return f"⚠️ Error al buscar propiedad: {str(e)[:100]}"
