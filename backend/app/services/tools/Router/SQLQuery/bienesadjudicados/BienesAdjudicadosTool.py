from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib import response

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from app.services.tools.Router.SQLQuery.filterbase import STOPWORDS, extraer_filtros

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
        # hard limits
        limit = max(1, min(int(limit), 50))

        filtros_adicionales = filtros_adicionales or extraer_filtros(q or "")

        select_cols = ", ".join(f"`{c}`" for c in DEFAULT_SELECT_COLS)

        where = []
        params: Dict[str, Any] = {"limit": limit}

        def add_like(field: str, value: Optional[str], param_name: str):
            if value:
                where.append(f"LOWER(`{field}`) LIKE :{param_name}")
                params[param_name] = f"%{value.lower()}%"

            if q:
                terms = [t.strip().lower() for t in q.split()
                    if t.strip() and t.lower() not in STOPWORDS and len(t.strip()) >= 3]
                term_blocks = []

                # ✅ Si no quedó nada útil, NO busques todo el catálogo
                if not terms and not any([provincia, canton, tipo, estado, precio_min, precio_max]):
                    return []
                for i, term in enumerate(terms):
                    ors = []
                    for j, col in enumerate(TEXT_SEARCH_COLS):
                        pn = f"t_{i}_{j}"
                        ors.append(f"LOWER(`{col}`) LIKE :{pn}")
                        params[pn] = f"%{term}%"
                    term_blocks.append("(" + " OR ".join(ors) + ")")
                if term_blocks:
                    where.append("(" + " OR ".join(term_blocks) + ")")

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
        print ("Ejecutando SQL:", sql)
        print ("Con parámetros:", params)
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()

        # devuelve lista de dicts serializable

        if not rows:
             return []
        return [dict(r) for r in rows]
