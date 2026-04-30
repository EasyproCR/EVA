"""
Customer Data Service - Procesa búsquedas de clientes personales ADM
Solo devuelve clientes asignados a asesores con rol administrativo (ADM/super_admin).
"""

import logging
import re
from typing import Optional, Dict, List, Any
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Roles que califican como "administrativos / ADM"
ADM_ROLES = ('administrator', 'super_admin')


class CustomerDataService:
    """
    Servicio para procesar consultas sobre clientes personales.
    IMPORTANTE: Solo devuelve clientes del área administrativa (ADM).
    Permite buscar por nombre, necesidades (lote en, casa en) y ubicación.
    """

    def __init__(self, sql_database=None):
        self.sql_database = sql_database
        logger.info("✓ CustomerDataService inicializado")

    def process_query(self, query: str) -> str:
        """Procesa una consulta de búsqueda de clientes ADM."""
        if not self.sql_database:
            logger.error("❌ SQL Database no configurada en CustomerDataService")
            return "⚠️ Servicio de clientes no disponible temporalmente."

        try:
            search_terms = self._extract_search_terms(query)
            if not search_terms:
                return (
                    "❓ No pude detectar qué estás buscando.\n\n"
                    "Ejemplos:\n"
                    "• *¿Qué clientes buscan casa en Upala?*\n"
                    "• *¿Cuáles clientes son de Heredia?*\n"
                    "• *Busca al cliente Juan Pérez*"
                )

            results = self._search_customers(search_terms)

            if not results:
                term_display = search_terms.replace("nombre:", "").strip()
                return (
                    f"📭 No encontré clientes ADM con: **'{term_display}'**\n\n"
                    "_Solo se muestran clientes asignados al área administrativa (ADM)._"
                )

            response = f"👥 **CLIENTES ADM ENCONTRADOS ({len(results)})**\n"
            response += f"Búsqueda: *'{search_terms.replace('nombre:', '').strip()}'*\n\n"

            for idx, row in enumerate(results, 1):
                name = row.get('full_name', 'Sin nombre')
                phone = row.get('phone_number', 'Sin teléfono')
                need = row.get('customer_need', 'No especificada')
                address = row.get('address', 'No especificada')
                advisor = row.get('advisor_name', 'Sin asesor')
                next_action = row.get('next_action', '')
                next_date = row.get('next_action_date', '')

                response += f"{idx}. **{name}** (Asesor: {advisor})\n"
                response += f"   📞 {phone}\n"
                response += f"   🎯 Necesidad: {need}\n"
                response += f"   📍 {address}\n"
                if next_action:
                    date_str = f" — {next_date}" if next_date else ""
                    response += f"   📋 {next_action}{date_str}\n"
                response += "\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en CustomerDataService: {str(e)}", exc_info=True)
            return f"⚠️ Ocurrió un error buscando los clientes: {str(e)[:100]}"

    def _extract_search_terms(self, query: str) -> Optional[str]:
        """Extrae el término de búsqueda de la consulta del usuario."""
        query_lower = query.lower()

        # Patrones para buscar por nombre de cliente
        name_patterns = [
            r'cliente\s+(?:llamado\s+|que\s+se\s+llama\s+|de\s+nombre\s+)?([A-Za-záéíóúÁÉÍÓÚñÑ][A-Za-záéíóúÁÉÍÓÚñÑ\s]{2,30})',
            r'busca(?:r)?\s+(?:al?\s+)?(?:cliente\s+)?([A-Za-záéíóúÁÉÍÓÚñÑ][A-Za-záéíóúÁÉÍÓÚñÑ\s]{2,30})',
            r'(?:ubica(?:r)?|encuentra)\s+(?:al?\s+)?([A-Za-záéíóúÁÉÍÓÚñÑ][A-Za-záéíóúÁÉÍÓÚñÑ\s]{2,30})',
            r'información\s+(?:de|del)\s+(?:cliente\s+)?([A-Za-záéíóúÁÉÍÓÚñÑ][A-Za-záéíóúÁÉÍÓÚñÑ\s]{2,30})',
        ]

        # Patrones para buscar necesidades (lote en, casa en, propiedad en)
        need_patterns = [
            r'buscan\s+(lote\s+en\s+.*?|casa\s+en\s+.*?|propiedad\s+en\s+.*?)(?:\?|$)',
            r'buscan\s+(.*?)(?:\?|$)',
            r'necesitan\s+(.*?)(?:\?|$)',
            r'quieren\s+(.*?)(?:\?|$)',
            r'interesados?\s+en\s+(.*?)(?:\?|$)',
        ]

        # Patrones para buscar por ubicación (son de, viven en)
        location_patterns = [
            r'son\s+de\s+(.*?)(?:\?|$)',
            r'viven\s+en\s+(.*?)(?:\?|$)',
            r'ubicados?\s+en\s+(.*?)(?:\?|$)',
        ]

        for pattern in name_patterns:
            match = re.search(pattern, query_lower)
            if match:
                term = match.group(1).strip().rstrip('?').strip()
                if term and len(term) > 2:
                    return f"nombre:{term}"

        for pattern in need_patterns:
            match = re.search(pattern, query_lower)
            if match:
                term = match.group(1).strip().rstrip('?').strip()
                if term and len(term) > 2:
                    return term

        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                term = match.group(1).strip().rstrip('?').strip()
                if term and len(term) > 2:
                    return term

        return None

    def _search_customers(self, search_terms: str) -> List[Dict[str, Any]]:
        """
        Búsqueda en BD restringida a clientes ADM.
        Solo trae clientes donde el asesor tiene rol administrator o super_admin.
        """
        is_name_search = search_terms.startswith("nombre:")
        if is_name_search:
            name_term = search_terms[7:].strip()
            words = [w for w in name_term.lower().split() if len(w) > 1]
        else:
            clean_term = search_terms.replace("?", "").strip()
            words = [
                w for w in clean_term.lower().split()
                if len(w) > 2 and w not in {'los', 'las', 'del', 'que', 'con', 'por', 'una', 'uno', 'como'}
            ]

        if not words:
            words = [search_terms.lower().replace("nombre:", "").strip()]

        params = {}

        if is_name_search:
            conds = []
            for i, word in enumerate(words):
                params[f"w{i}"] = f"%{word}%"
                conds.append(f"LOWER(pc.full_name) LIKE :w{i}")
            where_clause = "(" + " AND ".join(conds) + ")"
        else:
            need_conds, addr_conds = [], []
            for i, word in enumerate(words):
                params[f"w{i}"] = f"%{word}%"
                need_conds.append(f"LOWER(pc.customer_need) LIKE :w{i}")
                addr_conds.append(f"LOWER(pc.address) LIKE :w{i}")
            need_sql = " AND ".join(need_conds)
            addr_sql = " AND ".join(addr_conds)
            where_clause = f"(({need_sql}) OR ({addr_sql}))"

        # Filtro ADM inline (administrator o super_admin)
        roles_in = ", ".join([f"'{r}'" for r in ADM_ROLES])

        sql = f"""
        SELECT DISTINCT
            pc.full_name,
            pc.phone_number,
            pc.customer_need,
            pc.address,
            pc.next_action,
            pc.next_action_date,
            u.name AS advisor_name
        FROM personal_customers pc
        LEFT JOIN users u ON pc.user_id = u.id
        INNER JOIN model_has_roles mhr
            ON mhr.model_id = u.id
            AND mhr.model_type = 'App\\\\Models\\\\User'
        INNER JOIN roles r
            ON r.id = mhr.role_id
            AND r.name IN ({roles_in})
        WHERE {where_clause}
        ORDER BY pc.created_at DESC
        LIMIT 25
        """

        try:
            engine = self.sql_database._engine
            with engine.connect() as conn:
                result = conn.execute(text(sql), params)
                rows = result.mappings().all()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Error SQL en _search_customers: {str(e)}")
            raise
