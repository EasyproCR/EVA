from __future__ import annotations

from typing import Any, Dict, List, Optional

from llama_index.core.base.response.schema import Response
from llama_index.core.base.base_query_engine import BaseQueryEngine
# Import callback manager (varía por versión)
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

    # ✅ sync query (RouterQueryEngine lo usa)
    def _query(self, query_bundle) -> str:
        user_query = str(query_bundle)

        rows = self.bienes_db.buscar(q=user_query, limit=20)

        if not isinstance(rows, list):
            return Response(response="No encontré resultados.")

        

        lines = []
        for r in rows[:10]:
            lines.append(
                f"- {r.get('nombre')} | {r.get('provincia')}, {r.get('canton')} | "
                f"USD {r.get('precio_usd')} | {r.get('property_url')}"
            )

        return Response(response="Resultados:\n" + "\n".join(lines))
        

    # ✅ async query requerido por la clase abstracta
    async def _aquery(self, query_bundle) -> str:
        # como tu acceso a DB es sync, lo dejamos sync por ahora
        return self._query(query_bundle)

    # ✅ requerido por la clase abstracta (para instrumentación/prompts)
    def _get_prompt_modules(self) -> Dict[str, Any]:
        return {}
