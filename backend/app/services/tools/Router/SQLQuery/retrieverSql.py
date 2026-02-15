from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
import logging

from llama_index.core.indices.struct_store import SQLTableRetrieverQueryEngine
from llama_index.core.objects import SQLTableNodeMapping, ObjectIndex, SQLTableSchema
from llama_index.core import VectorStoreIndex
from llama_index.core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

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
        self.table_catalog = table_catalog or {}
        self.config = config or TableRetrieverConfig()

        logger.info(f"Inicializando RetrieverSQL con {len(self.table_catalog)} tablas en catálogo")
        
        # Construir el index/engine
        self._obj_index = self._build_table_object_index()
        self._query_engine = self._build_query_engine()
        
        logger.info("✓ RetrieverSQL configurado correctamente")

    # ---------- Public API ----------
    def get_query_engine(self):
        return self._query_engine

    def query(self, query: str):
        nodes = self._obj_index.as_retriever(similarity_top_k=self.config.similarity_top_k).retrieve(query)
        selected_tables = [n.node.metadata.get("table_name") for n in nodes if hasattr(n, "node")]
        logger.info(f"📊 Tablas seleccionadas para query: {selected_tables}")
        
        result = self._query_engine.query(query)
        logger.info(f"✓ Query ejecutado correctamente")
        return result

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

        logger.info(f"Indexando {len(all_table_names)} tablas: {all_table_names}")
        
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
        # ✅ PROMPT SQL MEJORADO - Mucho más detallado y con ejemplos
        SQL_PROMPT = PromptTemplate("""
        Eres un experto en SQL para MySQL

        Tu trabajo es generar consultas SQL CORRECTAS Y PRECISAS basadas en la pregunta del usuario.

        ═══════════════════════════════════════════════════════════════════
        REGLAS CRÍTICAS - SIEMPRE CUMPLIR
        ═══════════════════════════════════════════════════════════════════

        1. 🔍 BÚSQUEDA DE NOMBRES DE PERSONAS
        ❌ NUNCA uses igualdad exacta (=) para nombres
        ✅ SIEMPRE usa LIKE con % para búsquedas parciales
        ✅ Divide nombres compuestos y busca cada parte
        ✅ Usa LOWER() o comparación case-insensitive

        EJEMPLOS:
        
        Pregunta: "correo de Adrian Murillo"
        ❌ MAL: WHERE name = 'Adrian Murillo'
        ✅ BIEN:
        SELECT email, name 
        FROM usuarios 
        WHERE LOWER(name) LIKE '%adrian%' 
            AND LOWER(name) LIKE '%murillo%'
        
        Pregunta: "teléfono de María"
        ✅ BIEN:
        SELECT phone, name 
        FROM usuarios 
        WHERE LOWER(name) LIKE '%maria%' 
            OR LOWER(name) LIKE '%maría%'

        2. 📊 SELECCIÓN DE COLUMNAS
        ✅ Siempre incluye la columna por la que buscas
        ✅ Incluye contexto útil (nombre, ID, etc.)
        
        EJEMPLO:
        Pregunta: "correo de Juan"
        ✅ SELECT email, name, id FROM usuarios WHERE...
        ❌ SELECT email FROM usuarios WHERE...  (falta nombre para confirmar)

        3. 🔢 LÍMITES Y ORDENAMIENTO
        ✅ Usa LIMIT si esperas muchos resultados
        ✅ Ordena por relevancia cuando sea útil
        
        SELECT * FROM productos 
        WHERE LOWER(nombre) LIKE '%laptop%' 
        ORDER BY precio ASC 
        LIMIT 20

        4. 🎯 JOINS Y RELACIONES
        ✅ Si necesitas datos de múltiples tablas, usa JOIN
        ✅ Explica las relaciones con ON claras
        
        SELECT u.name, u.email, p.nombre_producto, p.precio
        FROM usuarios u
        JOIN pedidos pd ON u.id = pd.usuario_id
        JOIN productos p ON pd.producto_id = p.id
        WHERE LOWER(u.name) LIKE '%carlos%'

        5. 📅 FECHAS Y RANGOS
        ✅ Usa funciones de fecha apropiadas
        ✅ Para "mes pasado", "esta semana", calcula con DATE_SUB, CURDATE()
        
        SELECT * FROM ventas 
        WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)

        6. 💡 AGREGACIONES
        ✅ Para contar, sumar, promediar: usa COUNT, SUM, AVG, GROUP BY
        
        Pregunta: "total de ventas por cliente"
        SELECT cliente_id, SUM(monto) as total, COUNT(*) as num_ventas
        FROM ventas
        GROUP BY cliente_id
        ORDER BY total DESC

        ═══════════════════════════════════════════════════════════════════
        FORMATO DE SALIDA
        ═══════════════════════════════════════════════════════════════════

        Devuelve ÚNICAMENTE el SQL válido, sin:
        - Explicaciones antes o después
        - Markdown (sin ```)
        - Comentarios SQL (-- o /* */)
        - Texto adicional

        SOLO el SQL puro y ejecutable.

        ═══════════════════════════════════════════════════════════════════
        CONTEXTO DE LA BASE DE DATOS
        ═══════════════════════════════════════════════════════════════════

        {schema}

        ═══════════════════════════════════════════════════════════════════
        PREGUNTA DEL USUARIO
        ═══════════════════════════════════════════════════════════════════

        {query_str}

        ═══════════════════════════════════════════════════════════════════
        TU RESPUESTA (SOLO SQL)
        ═══════════════════════════════════════════════════════════════════
        """)

        table_retriever = self._obj_index.as_retriever(
            similarity_top_k=self.config.similarity_top_k
        )
        
        return SQLTableRetrieverQueryEngine(
            sql_database=self.sql_database,
            table_retriever=table_retriever,
            text_to_sql_prompt=SQL_PROMPT,  # ✅ Usa el parámetro correcto
            sql_only=False,  # ✅ Cambiado a False para obtener respuestas interpretadas
        )
