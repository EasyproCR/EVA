"""
Quotes Generation Engine - Genera cotizaciones formales para propiedades
Accesible para todos los usuarios.
"""

import logging
import re
from typing import Optional, Dict, Tuple
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from llama_index.core import Settings
from sqlalchemy import text

logger = logging.getLogger(__name__)

class QuotesGenerationEngine(BaseQueryEngine):
    """
    Query Engine para generar cotizaciones financieras de propiedades.
    Realiza cálculos de cuota matemática y utiliza el LLM para redactar un documento formal.
    """

    def __init__(self, sql_database=None):
        super().__init__(callback_manager=CallbackManager([]))
        self.sql_database = sql_database
        logger.info("✓ QuotesGenerationEngine inicializado")

    def _extract_property_id(self, query: str) -> Optional[int]:
        """Extrae el ID de la propiedad de la consulta."""
        patterns = [
            r'(?:id|propiedad|inmueble|casa|lote|terreno)\s+#?(\d+)',
            r'#(\d+)',
            r'(?:del|la)\s+(?:inmueble|propiedad)\s+(\d+)'
        ]
        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                return int(match.group(1))
        return None

    def _extract_financial_vars(self, query: str) -> Tuple[float, int, float]:
        """
        Extrae prima (%), plazo (años), y tasa de interés (%) de la consulta.
        Si no se encuentran, utiliza valores por defecto: 10% prima, 30 años, 8.5% interés.
        """
        query_lower = query.lower()
        
        # Valores por defecto
        prima_pct = 10.0
        plazo_anios = 30
        tasa_interes = 8.5
        
        # Extraer prima (ej. "15% de prima", "prima del 20")
        prima_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:de\s*)?prima', query_lower)
        if not prima_match:
            prima_match = re.search(r'prima\s*(?:del\s*)?(\d+(?:\.\d+)?)', query_lower)
        if prima_match:
            prima_pct = float(prima_match.group(1))

        # Extraer plazo (ej. "25 años", "a 20 años")
        plazo_match = re.search(r'(\d+)\s*a[ñn]os?', query_lower)
        if plazo_match:
            plazo_anios = int(plazo_match.group(1))

        # Extraer tasa (ej. "8.5% de interés", "tasa del 9%")
        tasa_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:de\s*)?(?:inter[ée]s|tasa)', query_lower)
        if not tasa_match:
            tasa_match = re.search(r'tasa\s*(?:del\s*)?(\d+(?:\.\d+)?)', query_lower)
        if tasa_match:
            tasa_interes = float(tasa_match.group(1))

        return prima_pct, plazo_anios, tasa_interes

    def _get_property_data(self, property_id: int) -> Optional[Dict]:
        """Obtiene datos básicos de la propiedad desde la BD."""
        if not self.sql_database:
            return None
        try:
            connection = self.sql_database._engine.connect()
            sql = """
            SELECT
                id, name, price, location, property_type, bank_name
            FROM properties
            WHERE id = :property_id
            LIMIT 1
            """
            result = connection.execute(text(sql), {'property_id': property_id})
            row = result.fetchone()
            connection.close()
            if row:
                return dict(row._mapping)
            return None
        except Exception as e:
            logger.error(f"Error obteniendo propiedad {property_id}: {e}")
            return None

    def _calculate_mortgage(self, price: float, prima_pct: float, plazo_anios: int, tasa_interes: float) -> Dict:
        """
        Calcula la cuota mensual utilizando la fórmula de amortización.
        """
        prima_monto = price * (prima_pct / 100.0)
        monto_prestamo = price - prima_monto
        
        r_mensual = (tasa_interes / 100.0) / 12.0
        n_meses = plazo_anios * 12
        
        if r_mensual > 0:
            cuota = monto_prestamo * (r_mensual * (1 + r_mensual)**n_meses) / ((1 + r_mensual)**n_meses - 1)
        else:
            cuota = monto_prestamo / n_meses if n_meses > 0 else 0
            
        ingreso_minimo = cuota / 0.40 # Regla general: la cuota no debe exceder 40% del ingreso
            
        return {
            "precio": price,
            "prima_pct": prima_pct,
            "prima_monto": prima_monto,
            "monto_prestamo": monto_prestamo,
            "plazo_anios": plazo_anios,
            "tasa_interes": tasa_interes,
            "cuota_mensual": cuota,
            "ingreso_minimo_requerido": ingreso_minimo
        }

    def _query(self, query_bundle: QueryBundle) -> Response:
        query = query_bundle.query_str
        logger.info(f"📝 Quotes Generation Request: {query}")

        property_id = self._extract_property_id(query)
        if not property_id:
            msg = (
                "Para generar una cotización necesito que me indiques el ID de la propiedad.\n\n"
                "Ejemplo: *'Generar cotización para la propiedad 150'* o *'Cotiza el ID 123 con 15% de prima a 25 años'*."
            )
            return Response(response=msg)

        property_data = self._get_property_data(property_id)
        if not property_data:
            return Response(response=f"Lo siento, no encontré la propiedad con ID {property_id} en la base de datos.")

        # Obtener precio (si viene nulo o 0, no podemos cotizar)
        price_val = property_data.get('price')
        if not price_val or float(price_val) <= 0:
            return Response(response=f"La propiedad {property_id} ({property_data.get('name')}) no tiene un precio válido registrado para cotizar.")
        
        price = float(price_val)
        
        # Extraer variables y calcular
        prima_pct, plazo_anios, tasa_interes = self._extract_financial_vars(query)
        calc = self._calculate_mortgage(price, prima_pct, plazo_anios, tasa_interes)
        
        # Generar texto de la cotización usando el LLM
        prompt = (
            "Eres un agente inmobiliario profesional. Redacta una cotización formal y atractiva para un cliente, "
            "basada estrictamente en los siguientes cálculos matemáticos y datos de la propiedad.\n\n"
            f"DATOS DE LA PROPIEDAD:\n"
            f"- Nombre: {property_data.get('name')}\n"
            f"- Tipo: {property_data.get('property_type')}\n"
            f"- Ubicación: {property_data.get('location')}\n"
            f"- Entidad: {property_data.get('bank_name', 'Bienes Adjudicados')}\n\n"
            f"CONDICIONES FINANCIERAS (Cálculos Exactos):\n"
            f"- Precio Total: ₡{calc['precio']:,.2f}\n"
            f"- Prima ({calc['prima_pct']}%): ₡{calc['prima_monto']:,.2f}\n"
            f"- Monto a Financiar: ₡{calc['monto_prestamo']:,.2f}\n"
            f"- Plazo: {calc['plazo_anios']} años\n"
            f"- Tasa de Interés Anual: {calc['tasa_interes']}%\n"
            f"- CUOTA MENSUAL ESTIMADA: ₡{calc['cuota_mensual']:,.2f}\n"
            f"- Ingreso Mínimo Sugerido: ₡{calc['ingreso_minimo_requerido']:,.2f}\n\n"
            "INSTRUCCIONES:\n"
            "1. Saluda formalmente e introduce la cotización.\n"
            "2. Presenta los datos financieros claramente (puedes usar viñetas o negritas).\n"
            "3. Incluye una pequeña nota aclarando que la cuota es estimada y está sujeta a aprobación crediticia y posibles seguros.\n"
            "4. Cierra con un llamado a la acción (CTA) para agendar una visita o iniciar el trámite.\n"
            "5. NO alteres los valores numéricos calculados, úsalos tal como están.\n\n"
            "Cotización:"
        )

        try:
            llm = Settings.llm
            response_text = llm.complete(prompt).text
            return Response(response=response_text)
        except Exception as e:
            logger.error(f"Error generando cotización con LLM: {e}")
            # Fallback a texto plano si falla el LLM
            fallback_text = (
                f"📊 **Cotización Estimada - Propiedad #{property_id}**\n\n"
                f"🏠 **{property_data.get('name')}**\n"
                f"📍 {property_data.get('location')} | 🏦 {property_data.get('bank_name')}\n\n"
                f"💰 **Precio Total:** ₡{calc['precio']:,.2f}\n"
                f"💵 **Prima ({calc['prima_pct']}%):** ₡{calc['prima_monto']:,.2f}\n"
                f"💳 **Monto a Financiar:** ₡{calc['monto_prestamo']:,.2f}\n\n"
                f"📅 **Plazo:** {calc['plazo_anios']} años\n"
                f"📈 **Tasa de Interés:** {calc['tasa_interes']}%\n\n"
                f"🧾 **Cuota Mensual Estimada:** ₡{calc['cuota_mensual']:,.2f}\n"
                f"💼 *Ingreso Mínimo Sugerido: ₡{calc['ingreso_minimo_requerido']:,.2f}*\n\n"
                f"*Nota: Valores estimados sujetos a políticas bancarias, aprobación y adición de pólizas.*"
            )
            return Response(response=fallback_text)

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        return self._query(query_bundle)

    def _get_prompt_modules(self):
        return {}
