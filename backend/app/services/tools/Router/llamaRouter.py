from __future__ import annotations

from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import PydanticSingleSelector
from llama_index.core.tools import QueryEngineTool,ToolMetadata,FunctionTool
from llama_index.core.query_engine import NLSQLTableQueryEngine
from app.services.tools.Router.DocumentsQuery import llamaDocuments

from app.services.tools.Router.SQLQuery.llamaSQLquery import LlamaSQLQuery
from app.services.tools.Router.SQLQuery.retrieverSql import RetrieverSQL, TableRetrieverConfig
from app.data import easycoreContext,bienesAdjudicados

from llama_index.core.selectors import PydanticSingleSelector
from llama_index.core.program import LLMTextCompletionProgram
from llama_index.core.output_parsers import PydanticOutputParser

from app.services.tools.Router.SQLQuery import BienesAdjudicadosTool

def _get_conn_uri(settings, key: str) -> str:
    """Obtiene una URI de conexión desde settings.

    Soporta, en orden:
    - settings.<key> (ej. DB_URI_BIENES)
    - settings.conexion[<key>] si existe (dict)
    """
    if hasattr(settings, key):
        uri = getattr(settings, key)
        if isinstance(uri, str) and uri.strip():
            return uri

    if hasattr(settings, "conexion"):
        conn_map = getattr(settings, "conexion")
        if isinstance(conn_map, dict) and key in conn_map and str(conn_map[key]).strip():
            return str(conn_map[key])

    raise ValueError(
        f"No encontré la conexión '{key}' en settings. "
        "Define un atributo con esa URI o agrega settings.conexion['<key>']."
    )


class LlamaRouter:
    """Router (LlamaIndex) para elegir entre herramientas de consulta (QueryEngineTools).

    Implementa el patrón:
    - 2 bases (2 QueryEngineTools SQL)
    - Cada SQL tool usa table retriever + ObjectIndex en el arranque
    - Docs tool (RAG documentos)
    - Internet queda fuera del router (placeholder con print)
    """

    def __init__(
        self,
        settings,
        db1_key: str = "DB_URI_BIENES",
        db2_key: str = "DB_URI_EASYCORE",
        sql_top_k_tables: int = 5,
    ):
        self.settings = settings

       

        # -------- SQL tool 1 (DB1) --------
        db1_uri = _get_conn_uri(settings, db1_key)
        engine_bienes = BienesAdjudicadosTool.BienesDB.build_engine(db1_uri)
        bienes_db = BienesAdjudicadosTool.BienesDB(engine_bienes)

        
        sql_db1_tool = FunctionTool.from_defaults(
            function=bienes_db.buscar,
            metadata=ToolMetadata(
            name="bienes adjudicados",
            description=(
               "Busca propiedades/bienes adjudicados en la vista vw_get_all_properties. "
                "Usa filtros: q (texto libre), provincia, canton, tipo, estado, precio_min, precio_max, limit."
            ),
            )
        )

        # -------- SQL tool 2 (DB2) --------
        db2_uri = _get_conn_uri(settings, db2_key)
        try:
            db2_sql_db = LlamaSQLQuery(db2_uri).get_sql_database()
        except Exception as e:
            raise ValueError(f"Error al conectar a DB2 con URI '{db2_uri}': {e}")
        db2_engine = RetrieverSQL(
            db2_sql_db,
            table_catalog=easycoreContext.TABLE_CATALOG_EASYCORE, 
            config=TableRetrieverConfig(similarity_top_k=6),
        ).get_query_engine()

        sql_db2_tool = QueryEngineTool(
            query_engine=db2_engine,
            metadata=ToolMetadata(
            name="easycore",
            description=(
                "Usar para preguntas sobre datos estructurados en la base EasyCore. "
                "Ejemplos: usuarios, ventas, inventario, facturas, operaciones internas, reportes."
            ),
            )
        )

        # -------- Router --------
        self.router = RouterQueryEngine(
            selector=PydanticSingleSelector.from_defaults( ),
            query_engine_tools=[
                sql_db1_tool,
                sql_db2_tool,
                
            ],
        )

    # -------- External placeholder (no router) --------
    def consultaInternet(self, query: str) -> str:
        print("Internet aún en desarrollo")
        return "Internet aún en desarrollo"

    # -------- Main API --------
    def query(self, user_query: str):
        return self.router.query(user_query)
