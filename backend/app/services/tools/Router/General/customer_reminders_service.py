"""
Customer Reminders Service - Muestra recordatorios de clientes para el usuario
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)


class CustomerRemindersService:
    """
    Servicio para procesar y mostrar recordatorios de clientes:
    - Citas pendientes de agendar
    - Seguimientos pendientes
    - Clientes sin actividad reciente
    """

    CUSTOMER_KEYWORDS = {
        'cliente', 'clientes', 'cita', 'citas', 'seguimiento', 'seguimientos',
        'agendar', 'agendar cita', 'recordatorio', 'recordatorios', 'contacto',
        'contactos', 'llamada', 'reunión', 'llamadas', 'reuniones'
    }

    def __init__(self, sql_database=None):
        """
        Args:
            sql_database: SQLDatabase instance from LlamaIndex
        """
        self.sql_database = sql_database
        logger.info("✓ CustomerRemindersService inicializado")

    def process_query(self, query: str, user_id: int, user_roles: List[str]) -> str:
        """
        Procesa una consulta sobre recordatorios de clientes

        Args:
            query: Pregunta del usuario
            user_id: ID del usuario autenticado
            user_roles: Roles del usuario

        Returns:
            Respuesta formateada en markdown
        """
        if not self.sql_database:
            logger.error("❌ SQL Database no configurada")
            return "⚠️ Servicio de recordatorios no disponible temporalmente."

        try:
            logger.info(f"  📞 Buscando recordatorios de clientes para usuario ID: {user_id}")
            return self._get_customer_reminders(user_id)

        except Exception as e:
            logger.error(f"❌ Error procesando recordatorios de clientes: {str(e)[:150]}", exc_info=True)
            return f"⚠️ Error al obtener recordatorios: {str(e)[:100]}"

    def _get_customer_reminders(self, user_id: int) -> str:
        """Obtiene todos los recordatorios de clientes del usuario"""
        try:
            response = "📞 **RECORDATORIOS DE CLIENTES**\n\n"

            # 1. Recordatorios pendientes
            pending_reminders = self._get_pending_reminders(user_id)
            if pending_reminders:
                response += pending_reminders

            # 2. Clientes sin seguimiento
            customers_no_followup = self._get_customers_pending_followup(user_id)
            if customers_no_followup:
                response += customers_no_followup

            # 3. Clientes sin cita agendada
            customers_no_appointment = self._get_customers_pending_appointment(user_id)
            if customers_no_appointment:
                response += customers_no_appointment

            if response == "📞 **RECORDATORIOS DE CLIENTES**\n\n":
                response = "✅ **¡Sin recordatorios pendientes!** Todos tus clientes están al día."

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_customer_reminders: {str(e)}")
            return f"⚠️ Error obteniendo recordatorios: {str(e)[:100]}"

    def _get_pending_reminders(self, user_id: int) -> str:
        """Obtiene recordatorios pendientes de la tabla customer_reminders"""
        try:
            sql = """
            SELECT
                cr.id,
                cr.reminder_type,
                cr.description,
                cr.reminder_date,
                cr.status,
                c.full_name,
                c.phone_number,
                c.email,
                c.property_name,
                c.created_at as customer_created_date
            FROM customer_reminders cr
            JOIN customers c ON cr.customer_id = c.id
            WHERE cr.user_id = :user_id
            AND cr.status = 'pending'
            AND cr.reminder_date IS NOT NULL
            ORDER BY cr.reminder_date ASC
            LIMIT 10
            """

            results = self._execute_query(sql, {'user_id': user_id})

            if not results:
                return ""

            response = "⏳ **RECORDATORIOS PENDIENTES**\n\n"

            for idx, row in enumerate(results, 1):
                reminder_type = row['reminder_type']
                type_emoji = "📅" if reminder_type == "appointment" else "📞"
                type_label = "CITA" if reminder_type == "appointment" else "SEGUIMIENTO"

                customer_name = row['full_name'] or '(sin nombre)'
                description = row['description'] or f"Recordatorio de {type_label.lower()}"
                reminder_date = row['reminder_date'] or '(sin fecha)'
                phone = row['phone_number'] or '(sin teléfono)'
                email = row['email'] or '(sin email)'
                property_name = row['property_name'] or '(sin propiedad especificada)'

                response += f"{idx}. {type_emoji} **{type_label}** - {customer_name}\n"
                response += f"   📝 {description}\n"
                response += f"   🏠 Propiedad: {property_name}\n"
                response += f"   📱 {phone} | 📧 {email}\n"
                response += f"   ⏰ Fecha: {reminder_date}\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_pending_reminders: {str(e)}")
            return ""

    def _get_customers_pending_followup(self, user_id: int) -> str:
        """Obtiene clientes que necesitan seguimiento"""
        try:
            sql = """
            SELECT
                c.id,
                c.full_name,
                c.phone_number,
                c.email,
                c.property_name,
                c.state,
                c.initial_contact_date,
                c.created_at,
                COUNT(cr.id) as reminder_count
            FROM customers c
            LEFT JOIN customer_reminders cr ON c.id = cr.customer_id AND cr.status = 'pending'
            WHERE c.user_id = :user_id
            AND (
                cr.reminder_type = 'follow_up' OR
                cr.reminder_type IS NULL
            )
            GROUP BY c.id
            HAVING reminder_count = 0
            LIMIT 10
            """

            results = self._execute_query(sql, {'user_id': user_id})

            if not results:
                return ""

            response = "📞 **CLIENTES PENDIENTES DE SEGUIMIENTO**\n\n"

            for idx, row in enumerate(results, 1):
                customer_name = row['full_name'] or '(sin nombre)'
                property_name = row['property_name'] or '(sin propiedad)'
                phone = row['phone_number'] or '(sin teléfono)'
                state = row['state'] or 'activo'
                initial_contact = row['initial_contact_date'] or '(sin fecha)'

                response += f"{idx}. 📞 **{customer_name}**\n"
                response += f"   🏠 Propiedad: {property_name}\n"
                response += f"   📱 {phone}\n"
                response += f"   🔴 Estado: {state.upper()}\n"
                response += f"   📅 Contacto inicial: {initial_contact}\n"
                response += f"   ✅ Acción: **Agendar seguimiento**\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_customers_pending_followup: {str(e)}")
            return ""

    def _get_customers_pending_appointment(self, user_id: int) -> str:
        """Obtiene clientes que necesitan cita agendada"""
        try:
            sql = """
            SELECT
                c.id,
                c.full_name,
                c.phone_number,
                c.email,
                c.property_name,
                c.budget_usd,
                c.budget_crc,
                c.state,
                c.created_at,
                COUNT(cr.id) as appointment_count
            FROM customers c
            LEFT JOIN customer_reminders cr
                ON c.id = cr.customer_id
                AND cr.reminder_type = 'appointment'
                AND cr.status = 'pending'
            WHERE c.user_id = :user_id
            AND c.state IS NOT NULL
            GROUP BY c.id
            HAVING appointment_count = 0
            ORDER BY c.created_at DESC
            LIMIT 8
            """

            results = self._execute_query(sql, {'user_id': user_id})

            if not results:
                return ""

            response = "📅 **CLIENTES SIN CITA AGENDADA**\n\n"

            for idx, row in enumerate(results, 1):
                customer_name = row['full_name'] or '(sin nombre)'
                property_name = row['property_name'] or '(sin propiedad)'
                phone = row['phone_number'] or '(sin teléfono)'
                email = row['email'] or '(sin email)'
                budget = row['budget_usd'] or row['budget_crc'] or '(sin presupuesto)'

                response += f"{idx}. 📅 **{customer_name}**\n"
                response += f"   🏠 Propiedad: {property_name}\n"
                response += f"   💰 Presupuesto: {budget}\n"
                response += f"   📱 {phone} | 📧 {email}\n"
                response += f"   ✅ Acción: **Agendar cita**\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_customers_pending_appointment: {str(e)}")
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

    def get_pending_reminders_for_greeting(self, user_id: int) -> dict:
        """
        Obtiene recordatorios pendientes para mostrar en el saludo inicial.
        Formato optimizado para el mensaje de bienvenida.
        """
        try:
            sql = """
            SELECT
                cr.id,
                cr.reminder_type,
                cr.description,
                cr.reminder_date,
                c.full_name,
                c.phone_number,
                c.property_name
            FROM customer_reminders cr
            JOIN customers c ON cr.customer_id = c.id
            WHERE cr.user_id = :user_id
            AND cr.status = 'pending'
            AND cr.reminder_date IS NOT NULL
            ORDER BY cr.reminder_date ASC
            LIMIT 5
            """

            results = self._execute_query(sql, {'user_id': user_id})

            if not results:
                return {"count": 0, "reminders": []}

            reminders = []
            for row in results:
                reminder_type = row['reminder_type']
                emoji = "📅" if reminder_type == "appointment" else "📞"
                tipo_label = "Cita" if reminder_type == "appointment" else "Seguimiento"

                customer_name = row['full_name'] or 'Cliente'
                description = row['description'] or f"{tipo_label} con {customer_name}"
                reminder_date = row['reminder_date']

                reminders.append({
                    'emoji': emoji,
                    'titulo': f"{tipo_label}: {customer_name}",
                    'descripcion': description,
                    'fecha_vencimiento': str(reminder_date) if reminder_date else '',
                    'accion': 'Agendar cita' if reminder_type == "appointment" else 'Hacer seguimiento'
                })

            return {"count": len(reminders), "reminders": reminders}

        except Exception as e:
            logger.error(f"❌ Error en get_pending_reminders_for_greeting: {str(e)}")
            return {"count": 0, "reminders": [], "error": str(e)}
