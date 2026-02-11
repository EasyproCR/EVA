from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from llama_index.core.indices.struct_store import SQLTableRetrieverQueryEngine
from llama_index.core.objects import SQLTableNodeMapping, ObjectIndex, SQLTableSchema
from llama_index.core import VectorStoreIndex


@dataclass
class TableRetrieverConfig:
    similarity_top_k: int = 6


class RetrieverSQL:
    """Construye un QueryEngine SQL con *table retrieval* (selección semántica de tablas).

    Patrón:
    - Indexa el *schema* (tablas) en un ObjectIndex (VectorStoreIndex)
    - Por cada query: recupera top-k tablas → genera/ejecuta SQL con ese subconjunto

    Esto escala mucho mejor cuando hay decenas de tablas y/o múltiples bases.
    """

    def __init__(self, sql_database, table_catalog: Optional[dict] = None, config: Optional[TableRetrieverConfig] = None):
        self.sql_database = sql_database
        self.table_catalog = table_catalog or {}   # ✅ primero
        self.config = config or TableRetrieverConfig()

        # luego ya puedes construir el index/engine
        self._obj_index = self._build_table_object_index()
        self._query_engine = self._build_query_engine()

    # ---------- Public API ----------
    def get_query_engine(self):
        return self._query_engine

    def query(self, query: str):
        nodes = self._obj_index.as_retriever(similarity_top_k=self.config.similarity_top_k).retrieve(query)
        print("Tablas elegidas:", [n.node.metadata.get("table_name") for n in nodes if hasattr(n, "node")])
        return self._query_engine.query(query)

    # ---------- Internal ----------
    def _get_all_table_names(self) -> List[str]:
        # Compatibilidad con distintas versiones de LlamaIndex
        if hasattr(self.sql_database, "get_usable_table_names"):
            return list(self.sql_database.get_usable_table_names())
        if hasattr(self.sql_database, "get_table_names"):
            return list(self.sql_database.get_table_names())
        return []

    def _table_context_str(self, table_name: str) -> str:
        # Intenta obtener info real (columnas, etc.) desde SQLDatabase
        if table_name in self.table_catalog:
            return self.table_catalog[table_name][:1200]
        return f"Tabla: {table_name}"

    def _build_table_object_index(self):
        all_table_names = self._get_all_table_names()
        if self.table_catalog:
            allowed = set(self.table_catalog.keys())
            all_table_names = [t for t in all_table_names if t in allowed]
        if not all_table_names:
            raise ValueError("No encontré tablas para indexar en SQLDatabase. Revisa la conexión y el catálogo.")

        table_node_mapping = SQLTableNodeMapping(self.sql_database)

        table_schema_objs = [
            SQLTableSchema(
                table_name=table_name,
                context_str=self._table_context_str(table_name),
            )
            for table_name in all_table_names
        ]

        return ObjectIndex.from_objects(
            table_schema_objs,
            table_node_mapping,
            VectorStoreIndex,
        )

    def _build_query_engine(self):
        table_retriever = self._obj_index.as_retriever(
            similarity_top_k=self.config.similarity_top_k
        )
        return SQLTableRetrieverQueryEngine(
            sql_database=self.sql_database,
            table_retriever=table_retriever,
        )
