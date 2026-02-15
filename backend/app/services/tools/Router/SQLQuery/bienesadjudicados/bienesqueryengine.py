"""
BienesQueryEngine Mejorado - Sugiere al usuario cómo obtener más detalles
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from llama_index.core.base.response.schema import Response
from llama_index.core.base.base_query_engine import BaseQueryEngine

try:
    from llama_index.core.callbacks import CallbackManager
except Exception:
    from llama_index.core.callbacks.base import CallbackManager


class BienesQueryEngine(BaseQueryEngine):
    def __init__(self, bienes_db, callback_manager: Optional[CallbackManager] = None):
        if callback_manager is None:
            callback_manager = CallbackManager([])

        super().__init__(callback_manager=callback_manager)
        self.bienes_db = bienes_db

    def _query(self, query_bundle) -> Response:
        user_query = str(query_bundle)

        rows = self.bienes_db.buscar(q=user_query, limit=20)

        if not isinstance(rows, list) or len(rows) == 0:
            return Response(response="No encontré resultados para tu búsqueda.")

        # ✅ NUEVO: Formatear resultados con sugerencias
        lines = ["**Resultados:**\n"]
        
        for i, r in enumerate(rows[:10], 1):  # ✅ Numerados
            precio = r.get('precio_usd')
            precio_str = f"USD {float(precio):,.0f}" if precio else "Precio no disponible"
            
            lines.append(
                f"{i}. **{r.get('nombre')}** | "
                f"{r.get('provincia')}, {r.get('canton')} | "
                f"{precio_str} | "
                f"[Ver en web]({r.get('property_url')})"
            )
        
        # ✅ NUEVO: Añadir sugerencias al usuario
        lines.append("\n---\n")
        lines.append("💡 **¿Quieres más detalles?**")
        lines.append("Puedes decirme:")
        lines.append("• _\"Dime más sobre la #1\"_ (para cualquier número)")
        lines.append("• _\"Info detallada del terreno en Moravia\"_ (por nombre/ubicación)")
        lines.append("• _O pega el enlace directo para análisis completo_")

        return Response(response="\n".join(lines))

    async def _aquery(self, query_bundle) -> Response:
        return self._query(query_bundle)

    def _get_prompt_modules(self) -> Dict[str, Any]:
        return {}
