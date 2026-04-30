"""
Customer Data Service - Procesa búsquedas de clientes personales
"""

import logging
import re
from typing import Optional, Dict, List, Any
from sqlalchemy import text

logger = logging.getLogger(__name__)

class CustomerDataService:
    """
    Servicio para procesar consultas sobre clientes personales.
    Permite buscar por necesidades (lote en, casa en) y ubicación (son de, viven en).
    """

    def __init__(self, sql_database=None):
        self.sql_database = sql_database
        logger.info("✓ CustomerDataService inicializado")

    def process_query(self, query: str) -> str:
        """Procesa una consulta de búsqueda de clientes."""
        if not self.sql_database:
            logger.error("❌ SQL Database no configurada en CustomerDataService")
            return "⚠️ Servicio de clientes no disponible temporalmente."

        try:
            # Extraer términos de búsqueda
            search_terms = self._extract_search_terms(query)
            if not search_terms:
                return "❓ No pude detectar qué estás buscando. Intenta algo como: '¿Qué clientes buscan casa en Upala?' o '¿Cuáles clientes son de Heredia?'"

            # Ejecutar búsqueda
            results = self._search_customers(search_terms)

            if not results:
                return f"📭 No encontré clientes personales con la necesidad o ubicación: **'{search_terms}'**"

            # Formatear respuesta
            response = f"👥 **CLIENTES PERSONALES ENCONTRADOS ({len(results)})**\n"
            response += f"Búsqueda: *'{search_terms}'*\n\n"

            for idx, row in enumerate(results, 1):
                name = row.get('full_name', 'Sin nombre')
                phone = row.get('phone_number', 'Sin teléfono')
                need = row.get('customer_need', 'No especificada')
                address = row.get('address', 'No especificada')
                advisor = row.get('advisor_name', 'Sin asesor')

                response += f"{idx}. **{name}** (Asesor: {advisor})\n"
                response += f"   📞 Teléfono: {phone}\n"
                response += f"   🎯 Necesidad: {need}\n"
                response += f"   📍 Dirección: {address}\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en CustomerDataService: {str(e)}", exc_info=True)
            return f"⚠️ Ocurrió un error buscando los clientes: {str(e)[:100]}"

    def _extract_search_terms(self, query: str) -> Optional[str]:
        """Extrae el término de búsqueda de la consulta del usuario."""
        query_lower = query.lower()
        
        # Patrones para buscar necesidades (lote en, casa en, propiedad en, buscan)
        need_patterns = [
            r'buscan\s+(lote\s+en\s+.*?|casa\s+en\s+.*?|propiedad\s+en\s+.*?)(?:\?|$)',
            r'buscan\s+(.*?)(?:\?|$)',
            r'necesitan\s+(.*?)(?:\?|$)',
            r'quieren\s+(.*?)(?:\?|$)'
        ]
        
        # Patrones para buscar direcciones (son de, viven en)
        location_patterns = [
            r'son\s+de\s+(.*?)(?:\?|$)',
            r'viven\s+en\s+(.*?)(?:\?|$)',
            r'ubicados\s+en\s+(.*?)(?:\?|$)'
        ]

        # Intentar extraer por necesidad
        for pattern in need_patterns:
            match = re.search(pattern, query_lower)
            if match:
                term = match.group(1).strip()
                if term and len(term) > 2:
                    return term

        # Intentar extraer por ubicación
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                term = match.group(1).strip()
                if term and len(term) > 2:
                    return term

        # Si no hay match con patrones, buscar si menciona directamente algo útil
        # pero es mejor retornar None si es muy genérico
        return None

    def _search_customers(self, search_terms: str) -> List[Dict[str, Any]]:
        """Realiza la búsqueda en la base de datos."""
        # Limpiar el término de búsqueda
        clean_term = search_terms.replace("?", "").strip()
        
        sql = """
        SELECT 
            pc.full_name, 
            pc.phone_number, 
            pc.customer_need, 
            pc.address, 
            u.name as advisor_name
        FROM personal_customers pc
        LEFT JOIN users u ON pc.user_id = u.id
        WHERE LOWER(pc.customer_need) LIKE :search_term 
           OR LOWER(pc.address) LIKE :search_term
        ORDER BY pc.created_at DESC
        LIMIT 20
        """
        
        try:
            engine = self.sql_database._engine
            with engine.connect() as conn:
                result = conn.execute(text(sql), {'search_term': f"%{clean_term.lower()}%"})
                rows = result.mappings().all()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Error SQL en _search_customers: {str(e)}")
            raise
