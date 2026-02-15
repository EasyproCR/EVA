from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from app.services.tools.Router.SQLQuery.filterbase import STOPWORDS, extraer_filtros

logger = logging.getLogger(__name__)

# ✅ Ajusta esta lista a tus columnas reales (DESCRIBE vw_get_all_properties;)
DEFAULT_SELECT_COLS = [
    "id",
    "nombre",
    "estado",
    "provincia",
    "canton",
    "distrito",
    "tipo_propiedad",
    "tipo_oferta",
    "precio_usd",
    "precio_local",
    "bedrooms",
    "bathrooms",
    "area_construccion",
    "tamanio_lote",
    "imagen",
    "property_url",
    "agent_name"
]

# Columnas donde se aplica búsqueda por texto (LIKE)
TEXT_SEARCH_COLS = [
    "nombre",
    "direccion",
    "provincia",
    "canton",
    "distrito",
    "tipo_propiedad",
    "tipo_bien",
    "agent_name",
    "nombre_banco"
]

@dataclass
class BienesDB:
    engine: Engine

    @staticmethod
    def build_engine(db_uri: str) -> Engine:
        # ✅ SiteGround/shared hosting: conexiones frágiles -> pre_ping + recycle corto
        logger.info(f"Creando engine de BD para Bienes Adjudicados")
        return create_engine(
            db_uri,
            pool_pre_ping=True,
            pool_recycle=300,  # 5 min
            connect_args={
                "connect_timeout": 10,
                "read_timeout": 60,
                "write_timeout": 60,
                "charset": "utf8mb4",
            },
        )

    def buscar(
        self,
        q: Optional[str] = None,
        provincia: Optional[str] = None,
        canton: Optional[str] = None,
        tipo: Optional[str] = None,
        estado: Optional[str] = None,
        precio_min: Optional[float] = None,
        precio_max: Optional[float] = None,
        limit: int = 25,
        filtros_adicionales: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Consulta controlada sobre vw_get_all_properties.
        - Sin introspección de schema.
        - Filtros con LIKE (case-insensitive).
        - LIMIT forzado para evitar cargas.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 BÚSQUEDA EN BIENES ADJUDICADOS")
        logger.info(f"{'='*60}")
        logger.info(f"Query texto: {q}")
        logger.info(f"Provincia: {provincia}, Cantón: {canton}, Tipo: {tipo}")
        logger.info(f"Precio: {precio_min} - {precio_max}, Estado: {estado}")
        
        # hard limits
        limit = max(1, min(int(limit), 50))

        # Extraer filtros del texto si no vienen explícitos
        if q and not any([provincia, canton, tipo, precio_max]):
            filtros_adicionales = filtros_adicionales or extraer_filtros(q)
            provincia = provincia or filtros_adicionales.get("provincia")
            precio_max = precio_max or filtros_adicionales.get("precio_max")
            logger.info(f"Filtros extraídos del texto: {filtros_adicionales}")

        select_cols = ", ".join(f"`{c}`" for c in DEFAULT_SELECT_COLS)

        where = []
        params: Dict[str, Any] = {"limit": limit}

        def add_like(field: str, value: Optional[str], param_name: str):
            if value:
                where.append(f"LOWER(`{field}`) LIKE :{param_name}")
                params[param_name] = f"%{value.lower()}%"

        # ✅ MEJORADO: Procesamiento de búsqueda de texto
        if q:
            # Limpiar y tokenizar
            terms = [t.strip().lower() for t in q.split()
                if t.strip() and t.lower() not in STOPWORDS and len(t.strip()) >= 2]  # ✅ Reducido a 2 caracteres mínimo
            
            logger.info(f"Términos de búsqueda después de filtrar stopwords: {terms}")
            
            # ✅ Si solo hay provincias/cantones como términos, no filtres tanto
            has_meaningful_terms = any(t not in [p.lower() for p in ["san jose", "alajuela", "heredia", "cartago", "guanacaste", "puntarenas", "limon"]] for t in terms)
            
            if terms:
                term_blocks = []
                for i, term in enumerate(terms):
                    ors = []
                    for j, col in enumerate(TEXT_SEARCH_COLS):
                        pn = f"t_{i}_{j}"
                        ors.append(f"LOWER(`{col}`) LIKE :{pn}")
                        params[pn] = f"%{term}%"
                    term_blocks.append("(" + " OR ".join(ors) + ")")
                
                if term_blocks:
                    # ✅ Usar OR entre términos para búsquedas más flexibles
                    where.append("(" + " OR ".join(term_blocks) + ")")
            elif not any([provincia, canton, tipo, estado, precio_min, precio_max]):
                # ✅ Si no hay términos útiles NI filtros, devolver vacío
                logger.warning("⚠️ Búsqueda muy amplia sin filtros específicos - devolviendo vacío")
                return []

        # Filtros específicos
        add_like("provincia", provincia, "provincia")
        add_like("canton", canton, "canton")
        add_like("tipo_propiedad", tipo, "tipo_propiedad")
        add_like("estado", estado, "estado")

        price_expr = "CAST(COALESCE(`precio_usd`, `precio_local`) AS DECIMAL(18,2))"

        if precio_min is not None:
            where.append(f"{price_expr} >= :precio_min")
            params["precio_min"] = float(precio_min)
        if precio_max is not None:
            where.append(f"{price_expr} <= :precio_max")
            params["precio_max"] = float(precio_max)

        where_sql = " AND ".join(where) if where else "1=1"

        sql = f"""
            SELECT {select_cols}
            FROM `vw_get_all_properties`
            WHERE {where_sql}
            ORDER BY ({price_expr} IS NULL), {price_expr} ASC
            LIMIT :limit
        """
        
        logger.info(f"\n📝 SQL GENERADO:")
        logger.info(f"{sql}")
        logger.info(f"\n🔧 PARÁMETROS:")
        logger.info(f"{params}")
        
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(text(sql), params).mappings().all()
            
            logger.info(f"✓ Query ejecutado - {len(rows)} resultados encontrados")
            
            if not rows:
                logger.warning("⚠️ No se encontraron resultados")
                return []
            
            # Mostrar preview de resultados
            if rows:
                logger.info(f"\n📊 PREVIEW DE RESULTADOS (primeros 3):")
                for i, row in enumerate(rows[:3], 1):
                    logger.info(f"  {i}. {row.get('nombre')} - {row.get('provincia')}, {row.get('canton')} - ${row.get('precio_usd')}")
            
            return [dict(r) for r in rows]
            
        except Exception as e:
            logger.error(f"❌ ERROR ejecutando query SQL: {e}", exc_info=True)
            raise
