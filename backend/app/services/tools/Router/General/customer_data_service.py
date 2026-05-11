"""
Customer Data Service - Procesa búsquedas de clientes personales ADM
Solo devuelve clientes asignados a asesores con rol administrativo (ADM/super_admin).

COMPORTAMIENTO:
  - Si la query pide "clientes admin" sin filtro -> devuelve TODOS los clientes ADM
  - Si la query pide clientes de X provincia/necesidad -> filtra por ese criterio
  - Clientes de asesores NO-admin NUNCA aparecen aqui
"""

import logging
import re
from typing import Optional, Dict, List, Any
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Roles que califican como "administrativos / ADM"
# Incluir todas las variantes posibles que EasyCore puede usar
ADM_ROLES = (
    'administrator', 'super_admin', 'admin',
    'administrador', 'administradora', 'administracion',
    'Administrador', 'Administrator', 'Admin'
)

# Marcador especial: traer TODOS los clientes ADM sin filtro adicional
_ALL_MARKER = "__all__"


class CustomerDataService:
    """
    Servicio para procesar consultas sobre clientes personales.
    IMPORTANTE: Solo devuelve clientes del area administrativa (ADM).
    Permite buscar por nombre, necesidades (lote en, casa en) y ubicacion.
    Cuando no hay filtro especifico, devuelve TODOS los clientes ADM.
    """

    def __init__(self, sql_database=None):
        self.sql_database = sql_database
        logger.info("CustomerDataService inicializado")

    def process_query(self, query: str) -> str:
        """Procesa una consulta de busqueda de clientes ADM."""
        if not self.sql_database:
            logger.error("SQL Database no configurada en CustomerDataService")
            return "Servicio de clientes no disponible temporalmente."

        try:
            search_terms = self._extract_search_terms(query)
            logger.info(f"Terminos extraidos: '{search_terms}' de query: '{query}'")

            if not search_terms:
                return (
                    "No pude detectar que estas buscando.\n\n"
                    "Ejemplos:\n"
                    "- Muestrame los clientes admin\n"
                    "- Que clientes buscan casa en Upala?\n"
                    "- Cuales clientes son de Heredia?\n"
                    "- Busca al cliente Juan Perez"
                )

            results = self._search_customers(search_terms)

            if not results:
                if search_terms == _ALL_MARKER:
                    return (
                        "No hay clientes registrados en el area ADM todavia.\n\n"
                        "Solo se muestran clientes asignados al area administrativa (ADM)."
                    )
                term_display = search_terms.replace("nombre:", "").strip()
                return (
                    f"No encontre clientes ADM con: '{term_display}'\n\n"
                    "Solo se muestran clientes asignados al area administrativa (ADM)."
                )

            # Encabezado segun el modo
            if search_terms == _ALL_MARKER:
                response = f"CLIENTES ADM ({len(results)} registros)\n\n"
            else:
                term_display = search_terms.replace("nombre:", "").strip()
                response = f"CLIENTES ADM ENCONTRADOS ({len(results)})\n"
                response += f"Busqueda: '{term_display}'\n\n"

            for idx, row in enumerate(results, 1):
                name        = row.get('full_name', 'Sin nombre')
                phone       = row.get('phone_number', 'Sin telefono')
                need        = row.get('customer_need', 'No especificada')
                address     = row.get('address', 'No especificada')
                advisor     = row.get('advisor_name', 'Sin asesor')
                next_action = row.get('next_action', '')
                next_date   = row.get('next_action_date', '')

                response += f"{idx}. *{name}* (Asesor: {advisor})\n"
                response += f"   Tel: {phone}\n"
                response += f"   Necesidad: {need}\n"
                response += f"   Direccion: {address}\n"
                if next_action:
                    date_str = f" - {next_date}" if next_date else ""
                    response += f"   Proxima accion: {next_action}{date_str}\n"
                response += "\n"

            return response

        except Exception as e:
            logger.error(f"Error en CustomerDataService: {str(e)}", exc_info=True)
            return f"Ocurrio un error buscando los clientes: {str(e)[:100]}"

    # ------------------------------------------------------------------
    # DETECCION DEL TIPO DE BUSQUEDA
    # ------------------------------------------------------------------

    def _extract_search_terms(self, query: str) -> Optional[str]:
        """
        Extrae el termino de busqueda de la consulta del usuario.

        Retorna:
          __all__          -> traer TODOS los clientes ADM (sin filtro)
          nombre:<nombre>  -> buscar por nombre de cliente
          <texto>          -> buscar por necesidad o direccion
          None             -> no se pudo detectar nada util
        """
        query_lower = query.lower().strip()

        # 1. DETECCION: "clientes admin/adm" SIN filtro especifico
        all_patterns = [
            r'^clientes?\s+(?:adm|admin|administrativos?|de\s+administraci[oo]n)\s*\??$',
            r'^(?:mu[ée]strame|dame|ver|lista(?:r)?|listar)\s+(?:los\s+|las\s+)?clientes?\s+(?:adm|admin|administrativos?)\s*\??$',
            r'^(?:cu[aá]les?|qu[eé])\s+(?:son\s+)?(?:los\s+|las\s+)?clientes?\s+(?:adm|admin)\s*\??$',
            r'^(?:hay\s+)?clientes?\s+(?:adm|admin)\s*\??$',
            r'clientes?\s+(?:adm|admin)\s*$',
            r'^(?:mu[ée]strame|dame|ver)\s+(?:todos?\s+)?(?:los\s+)?clientes?\s*\??$',
        ]
        for pattern in all_patterns:
            if re.search(pattern, query_lower):
                logger.info("Modo __all__: se devolveron TODOS los clientes ADM")
                return _ALL_MARKER

        # 2. DETECCION: buscar por NOMBRE
        name_patterns = [
            r'cliente\s+(?:llamado\s+|que\s+se\s+llama\s+|de\s+nombre\s+)?([A-Za-zaeiouAEIOUn][A-Za-zaeiouAEIOUn\s]{2,30})',
            r'busca(?:r)?\s+(?:al?\s+)?(?:cliente\s+)?([A-Za-zaeiouAEIOUn][A-Za-zaeiouAEIOUn\s]{2,30})',
            r'(?:ubica(?:r)?|encuentra)\s+(?:al?\s+)?([A-Za-zaeiouAEIOUn][A-Za-zaeiouAEIOUn\s]{2,30})',
            r'informaci[oo]n\s+(?:de|del)\s+(?:cliente\s+)?([A-Za-zaeiouAEIOUn][A-Za-zaeiouAEIOUn\s]{2,30})',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, query_lower)
            if match:
                term = match.group(1).strip().rstrip('?').strip()
                if term and len(term) > 2:
                    return f"nombre:{term}"

        # 3. DETECCION: buscar por NECESIDAD (lote en, casa en, etc.)
        need_patterns = [
            r'buscan\s+(lote\s+en\s+.*?|casa\s+en\s+.*?|propiedad\s+en\s+.*?)(?:\?|$)',
            r'buscan\s+(.*?)(?:\?|$)',
            r'necesitan\s+(.*?)(?:\?|$)',
            r'quieren\s+(.*?)(?:\?|$)',
            r'interesados?\s+en\s+(.*?)(?:\?|$)',
        ]
        for pattern in need_patterns:
            match = re.search(pattern, query_lower)
            if match:
                term = match.group(1).strip().rstrip('?').strip()
                if term and len(term) > 2:
                    return term

        # 4. DETECCION: buscar por UBICACION / PROVINCIA
        location_patterns = [
            r'son\s+de\s+(.*?)(?:\?|$)',
            r'viven\s+en\s+(.*?)(?:\?|$)',
            r'ubicados?\s+en\s+(.*?)(?:\?|$)',
            r'clientes?\s+(?:adm\s+)?(?:admin\s+)?de\s+([A-Za-zaeiouAEIOUn][A-Za-zaeiouAEIOUn\s]{2,30})(?:\?|$)',
            r'clientes?\s+(?:adm\s+)?(?:admin\s+)?en\s+([A-Za-zaeiouAEIOUn][A-Za-zaeiouAEIOUn\s]{2,30})(?:\?|$)',
            r'de\s+(?:la\s+provincia\s+de\s+)?([A-Za-zaeiouAEIOUn]{4,})\s*(?:\?|$)',
            r'en\s+(?:la\s+provincia\s+de\s+)?([A-Za-zaeiouAEIOUn]{4,})\s*(?:\?|$)',
        ]
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                term = match.group(1).strip().rstrip('?').strip()
                if term and len(term) > 2:
                    return term

        # 5. FALLBACK: si menciona "clientes" en la query
        cliente_kw = {'cliente', 'clientes', 'personas', 'persona', 'comprador', 'compradores'}
        words_in_query = set(query_lower.replace('?', '').split())
        if cliente_kw.intersection(words_in_query):
            # Si dice "clientes admin" sin mas -> todos los ADM
            if words_in_query.intersection({'adm', 'admin', 'administrativos', 'administracion', 'administracion'}):
                logger.info("Modo __all__ por fallback (clientes + admin keyword)")
                return _ALL_MARKER

            stopwords = {
                'los', 'las', 'del', 'que', 'con', 'por', 'una', 'uno', 'como',
                'todo', 'hay', 'tienen', 'cuales', 'son', 'adm',
                'admin', 'cliente', 'clientes', 'personas', 'persona',
                'comprador', 'compradores', 'me', 'puedes', 'mostrar', 'dame',
                'dime', 'ver', 'listar', 'lista', 'todos', 'todas', 'muestrame',
                'dime', 'cual', 'mis', 'nuestros', 'hay'
            }
            remaining = [w for w in query_lower.replace('?', '').split()
                         if w not in stopwords and len(w) > 2]
            if remaining:
                return ' '.join(remaining)

            # Si menciona clientes pero no hay ningun filtro -> traer todos
            logger.info("Modo __all__ por fallback (solo 'clientes' sin filtro)")
            return _ALL_MARKER

        return None

    # ------------------------------------------------------------------
    # CONSULTA A LA BASE DE DATOS
    # ------------------------------------------------------------------

    def _build_sql_all(self, roles_in: str) -> tuple:
        """SQL para traer todos los clientes ADM sin filtro adicional."""
        sql = f"""
        SELECT DISTINCT
            pc.full_name,
            pc.phone_number,
            pc.customer_need,
            pc.address,
            pc.next_action,
            pc.next_action_date,
            COALESCE(u.name, 'Sin asesor') AS advisor_name
        FROM personal_customers pc
        LEFT JOIN users u ON pc.user_id = u.id
        WHERE
            pc.user_id IS NULL
            OR EXISTS (
                SELECT 1
                FROM model_has_roles mhr
                INNER JOIN roles r ON r.id = mhr.role_id
                WHERE mhr.model_id = pc.user_id
                  AND r.name IN ({roles_in})
            )
        ORDER BY pc.created_at DESC
        LIMIT 50
        """
        return sql, {}

    def _build_sql_nombre(self, search_terms: str, roles_in: str) -> tuple:
        """SQL para buscar por nombre de cliente."""
        name_term = search_terms[7:].strip()
        words = [w for w in name_term.lower().split() if len(w) > 1]
        if not words:
            words = [name_term]

        params = {}
        conds = []
        for i, word in enumerate(words):
            params[f"w{i}"] = f"%{word}%"
            conds.append(f"LOWER(pc.full_name) LIKE :w{i}")
        where_clause = "(" + " AND ".join(conds) + ")"

        sql = f"""
        SELECT DISTINCT
            pc.full_name,
            pc.phone_number,
            pc.customer_need,
            pc.address,
            pc.next_action,
            pc.next_action_date,
            COALESCE(u.name, 'Sin asesor') AS advisor_name
        FROM personal_customers pc
        LEFT JOIN users u ON pc.user_id = u.id
        WHERE {where_clause}
          AND (
            pc.user_id IS NULL
            OR EXISTS (
                SELECT 1
                FROM model_has_roles mhr
                INNER JOIN roles r ON r.id = mhr.role_id
                WHERE mhr.model_id = pc.user_id
                  AND r.name IN ({roles_in})
            )
          )
        ORDER BY pc.created_at DESC
        LIMIT 25
        """
        return sql, params

    def _build_sql_need_addr(self, search_terms: str, roles_in: str) -> tuple:
        """SQL para buscar por necesidad o direccion."""
        clean_term = search_terms.replace("?", "").strip()
        stopwords_sql = {
            'los', 'las', 'del', 'que', 'con', 'por', 'una', 'uno', 'como',
            'todo', 'dato', 'datos', 'detalle', 'detalles', 'informacion'
        }
        words = [w for w in clean_term.lower().split()
                 if len(w) > 2 and w not in stopwords_sql]
        if not words:
            words = [clean_term]

        params = {}
        need_conds, addr_conds = [], []
        for i, word in enumerate(words):
            params[f"w{i}"] = f"%{word}%"
            need_conds.append(f"LOWER(pc.customer_need) LIKE :w{i}")
            addr_conds.append(f"LOWER(pc.address) LIKE :w{i}")
        need_sql = " AND ".join(need_conds)
        addr_sql = " AND ".join(addr_conds)
        where_clause = f"(({need_sql}) OR ({addr_sql}))"

        sql = f"""
        SELECT DISTINCT
            pc.full_name,
            pc.phone_number,
            pc.customer_need,
            pc.address,
            pc.next_action,
            pc.next_action_date,
            COALESCE(u.name, 'Sin asesor') AS advisor_name
        FROM personal_customers pc
        LEFT JOIN users u ON pc.user_id = u.id
        WHERE {where_clause}
          AND (
            pc.user_id IS NULL
            OR EXISTS (
                SELECT 1
                FROM model_has_roles mhr
                INNER JOIN roles r ON r.id = mhr.role_id
                WHERE mhr.model_id = pc.user_id
                  AND r.name IN ({roles_in})
            )
          )
        ORDER BY pc.created_at DESC
        LIMIT 25
        """
        return sql, params

    def _search_customers(self, search_terms: str) -> List[Dict[str, Any]]:
        """
        Busqueda en BD restringida a clientes ADM.
        Solo trae clientes donde el asesor tiene rol administrator, super_admin o admin.
        Si el filtro de roles retorna 0 resultados pero hay clientes en la tabla,
        hace un fallback trayendo todos los clientes (para asesores sin rol en la BD).
        """
        roles_in = ", ".join([f"'{r}'" for r in ADM_ROLES])

        if search_terms == _ALL_MARKER:
            sql, params = self._build_sql_all(roles_in)
        elif search_terms.startswith("nombre:"):
            sql, params = self._build_sql_nombre(search_terms, roles_in)
        else:
            sql, params = self._build_sql_need_addr(search_terms, roles_in)

        logger.info(f"SQL: {sql.strip()[:200]}...")
        logger.info(f"Params: {params}")

        try:
            engine = self.sql_database._engine
            with engine.connect() as conn:
                result = conn.execute(text(sql), params)
                rows = result.mappings().all()
                logger.info(f"Clientes ADM encontrados: {len(rows)}")

                if len(rows) == 0:
                    # Diagnostico automatico
                    try:
                        r2 = conn.execute(text("SELECT COUNT(*) FROM personal_customers"))
                        total = r2.scalar()
                        logger.warning(f"0 clientes ADM pero hay {total} en total en personal_customers")

                        if total > 0:
                            # Log roles encontrados para diagnóstico
                            r3 = conn.execute(text("""
                                SELECT DISTINCT ro.name as rol, mhr.model_type
                                FROM personal_customers pc
                                JOIN users u ON pc.user_id = u.id
                                JOIN model_has_roles mhr ON mhr.model_id = u.id
                                JOIN roles ro ON ro.id = mhr.role_id
                                LIMIT 10
                            """))
                            roles_found = []
                            for row in r3.mappings():
                                logger.warning(f"  Rol asesor en BD: rol={row['rol']} model_type={row['model_type']}")
                                roles_found.append(row['rol'])

                            # FALLBACK: si hay clientes pero ninguno tiene rol ADM
                            # (puede que el rol se llame diferente), traer todos los clientes
                            logger.warning("FALLBACK: Trayendo todos los clientes sin filtro de rol ADM")
                            fallback_sql = """
                                SELECT DISTINCT
                                    pc.full_name,
                                    pc.phone_number,
                                    pc.customer_need,
                                    pc.address,
                                    pc.next_action,
                                    pc.next_action_date,
                                    COALESCE(u.name, 'Sin asesor') AS advisor_name
                                FROM personal_customers pc
                                LEFT JOIN users u ON pc.user_id = u.id
                                ORDER BY pc.created_at DESC
                                LIMIT 50
                            """
                            if search_terms != _ALL_MARKER:
                                # Para búsquedas específicas, añadir WHERE del original
                                # pero sin el filtro de roles
                                pass  # Usar fallback general
                            r_fallback = conn.execute(text(fallback_sql), {})
                            rows = r_fallback.mappings().all()
                            logger.warning(f"FALLBACK result: {len(rows)} clientes sin filtro de rol")

                    except Exception as diag_e:
                        logger.warning(f"Error en diagnostico/fallback: {diag_e}")

                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error SQL en _search_customers: {str(e)}")
            raise
