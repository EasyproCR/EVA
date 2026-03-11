"""
BanksQueryEngine - Especializado en búsquedas de datos de bancos
Accede a la BD de Bienes Adjudicados para obtener info de bancos y sus propiedades
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging
from llama_index.core.base.response.schema import Response
from llama_index.core.base.base_query_engine import BaseQueryEngine
from app.services.tools.Router.utils.formatters import (
    format_price, format_location, group_by_key, count_by_key, safe_float
)

try:
    from llama_index.core.callbacks import CallbackManager
except Exception:
    from llama_index.core.callbacks.base import CallbackManager


logger = logging.getLogger(__name__)


class BanksQueryEngine(BaseQueryEngine):
    def __init__(self, bienes_db, callback_manager: Optional[CallbackManager] = None):
        if callback_manager is None:
            callback_manager = CallbackManager([])

        super().__init__(callback_manager=callback_manager)
        self.bienes_db = bienes_db

    def _query(self, query_bundle) -> Response:
        """Busca datos de bancos y sus propiedades en remate"""
        user_query = query_bundle.query_str

        logger.info(f"BUSQUEDA DE BANCOS: {user_query}")

        try:
            # Buscar propiedades asociadas a bancos
            rows = self.bienes_db.buscar(q=user_query, limit=50)

            if not isinstance(rows, list) or len(rows) == 0:
                return Response(
                    response="No encontre informacion de bancos para tu busqueda. "
                             "Podrias especificar un nombre de banco o hacer otra consulta?"
                )

            # Agrupar por banco
            bancos_dict = group_by_key(rows, 'nombre_banco')

            # Formatear respuesta
            lines = ["## Informacion de Bancos\n"]

            for banco, properties in sorted(bancos_dict.items()):
                lines.append(f"\n### {banco}")
                lines.append(f"Total de propiedades en remate: {len(properties)}\n")

                # Estadisticas por banco - SINGLE PASS (una sola iteracion)
                precios = []
                tipos = {}
                provincias = {}

                for prop in properties:
                    # Procesar precio
                    precio_float = safe_float(prop.get('precio_usd'))
                    if precio_float > 0:
                        precios.append(precio_float)

                    # Procesar tipo
                    tipo = prop.get('tipo_propiedad', 'Desconocido')
                    tipos[tipo] = tipos.get(tipo, 0) + 1

                    # Procesar provincia
                    prov = prop.get('provincia', 'Desconocido')
                    provincias[prov] = provincias.get(prov, 0) + 1

                # Mostrar estadisticas de precios
                if precios:
                    precio_promedio = sum(precios) / len(precios)
                    precio_min = min(precios)
                    precio_max = max(precios)
                    lines.append("Rango de precios:")
                    lines.append(f"   - Minimo: {format_price(precio_min)}")
                    lines.append(f"   - Maximo: {format_price(precio_max)}")
                    lines.append(f"   - Promedio: {format_price(precio_promedio)}\n")

                # Mostrar tipos de propiedades
                if tipos:
                    lines.append("Tipos de propiedades:")
                    for tipo, count in sorted(tipos.items(), key=lambda x: x[1], reverse=True):
                        lines.append(f"   - {tipo}: {count}")
                    lines.append("")

                # Mostrar provincias
                if provincias:
                    lines.append("Provincias con propiedades:")
                    for prov, count in sorted(provincias.items(), key=lambda x: x[1], reverse=True):
                        lines.append(f"   - {prov}: {count}")
                    lines.append("")

                # Mostrar primeras propiedades del banco
                lines.append("Primeras propiedades:")
                for i, prop in enumerate(properties[:5], 1):
                    nombre = prop.get('nombre', 'Sin nombre')
                    ubicacion = format_location(prop)
                    tipo = prop.get('tipo_propiedad', 'Desconocido')
                    precio = format_price(prop.get('precio_usd'))
                    agente = prop.get('agent_name', 'N/D')

                    lines.append(f"\n   {i}. {nombre}")
                    lines.append(f"      - Ubicacion: {ubicacion}")
                    lines.append(f"      - Tipo: {tipo}")
                    lines.append(f"      - Precio: {precio}")
                    lines.append(f"      - Agente: {agente}")

                if len(properties) > 5:
                    lines.append(f"\n   ... y {len(properties) - 5} propiedades mas")

                lines.append("\n---")

            lines.append("\nComandos que puedes usar:")
            lines.append("* 'Dime mas detalles del [numero]' - Ver propiedad especifica")
            lines.append("* '¿Cuales son las propiedades mas baratas de [banco]?'")
            lines.append("* 'Mostrar propiedades de [banco] en [provincia]'")

            return Response(response="\n".join(lines))

        except Exception as e:
            logger.error(f"Error en busqueda de bancos: {e}", exc_info=True)
            return Response(
                response=f"Hubo un error al buscar informacion de bancos: {str(e)}. "
                         "Por favor intenta de nuevo con una consulta diferente."
            )

    async def _aquery(self, query_bundle) -> Response:
        return self._query(query_bundle)

    def _get_prompt_modules(self) -> Dict[str, Any]:
        return {}
