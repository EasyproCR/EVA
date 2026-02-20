from __future__ import annotations
import logging
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

from app.services.tools.Router.General.general_query_engine import GeneralQueryEngine
from app.services.tools.Router.SQLQuery.bienesadjudicados import BienesAdjudicadosTool
from app.services.tools.Router.SQLQuery.bienesadjudicados.bienesqueryengine import BienesQueryEngine
from app.services.tools.Router.General.tavilyService import TavilyBienesQueryEngine


from app.services.tools.Router.General.property_question_engine import PropertyQuestionEngine
from app.services.conversation_context import ConversationContext
from app.services.tools.Router.SQLQuery.bienesadjudicados.propertydbservice import PropertyDatabaseService









# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        context_manager = ConversationContext()
    ):
        self.settings = settings
        self.context_manager = context_manager
        self.property_db_service = PropertyDatabaseService(connection_uri=_get_conn_uri(settings, "DB_URI_BIENES"))
        logger.info("Inicializando LlamaRouter...")

        # -------- SQL tool 1 (DB1 - Bienes Adjudicados) --------
        try:
            db1_uri = _get_conn_uri(settings, db1_key)
            engine_bienes = BienesAdjudicadosTool.BienesDB.build_engine(db1_uri)
            bienes_db = BienesAdjudicadosTool.BienesDB(engine_bienes)
            qe_bienes = BienesQueryEngine(bienes_db)
            
            sql_db1_tool = QueryEngineTool(
                query_engine=qe_bienes,
                metadata=ToolMetadata(
                    name="bienes_adjudicados",
                    description=(
                        "🏠 BASE DE DATOS DE PROPIEDADES Y BIENES RAÍCES EN COSTA RICA\n\n"
                        "USAR CUANDO el usuario pregunta sobre:\n"
                        "- Propiedades, casas, terrenos, lotes, fincas\n"
                        "- Bienes adjudicados o remates bancarios\n"
                        "- Búsquedas por ubicación (provincia, cantón, distrito)\n"
                        "- Precios de propiedades (USD o colones)\n"
                        "- Características: habitaciones, baños, área\n"
                        "- Tipos: residencial, comercial, agrícola\n"
                        "- Estados: disponible, vendido, reservado\n\n"
                        "EJEMPLOS:\n"
                        "✅ 'casas en San José'\n"
                        "✅ 'terrenos en Guanacaste bajo $100k'\n"
                        "✅ 'propiedades con 3 habitaciones'\n"
                        "✅ 'lotes en Escazú'\n\n"
                        "DATOS DISPONIBLES:\n"
                        "Vista: vw_get_all_properties\n"
                        "Campos: provincia, cantón, distrito, tipo_propiedad, precio_usd, "
                        "precio_local, bedrooms, bathrooms, area_construccion, tamanio_lote"
                    ),
                )
                
            )
            logger.info("✓ Tool 'bienes_adjudicados' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando bienes_adjudicados: {e}")
            raise

        # -------- SQL tool 2 (DB2 - Easycore) --------
        try:
            db2_uri = _get_conn_uri(settings, db2_key)
            db2_sql_db = LlamaSQLQuery(db2_uri).get_sql_database()
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
                        "💼 BASE DE DATOS INTERNA EASYCORE - OPERACIONES DE NEGOCIO\n\n"
                        "USAR CUANDO el usuario pregunta sobre:\n"
                        "- Usuarios, clientes, empleados, contactos\n"
                        "- Ventas, transacciones, facturas, pagos\n"
                        "- Inventario, productos, stock\n"
                        "- Reportes operativos internos\n"
                        "- Datos de personas (nombres, emails, teléfonos)\n"
                        "- Información corporativa o administrativa\n\n"
                        "EJEMPLOS:\n"
                        "✅ 'correo de Adrian Murillo'\n"
                        "✅ 'ventas del mes pasado'\n"
                        "✅ 'usuarios registrados esta semana'\n"
                        "✅ 'inventario de producto X'\n\n"
                        "NO USAR para propiedades o bienes raíces.\n"
                        "IMPORTANTE: Para nombres de personas, usa LIKE parcial, no igualdad exacta."
                    ),
                )
            )
            logger.info("✓ Tool 'easycore' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando easycore: {e}")
            raise

        #-------- General tool --------
        try:
            general_qe = GeneralQueryEngine()
            general_tool = QueryEngineTool(
                query_engine=general_qe,
                metadata=ToolMetadata(
                    name="general",
                    description=(
                        "💬 CONVERSACIÓN GENERAL - SIN DATOS ESPECÍFICOS\n\n"
                        "USAR CUANDO:\n"
                        "- Usuario saluda: 'hola', 'buenos días', '¿qué tal?'\n"
                        "- Preguntas generales sin necesidad de datos: '¿qué puedes hacer?'\n"
                        "- Consultas de conocimiento general: 'explícame qué es...'\n"
                        "- NO requiere acceso a bases de datos\n\n"
                        "NO USAR si el usuario menciona:\n"
                        "- Nombres de personas, empresas, productos específicos\n"
                        "- Propiedades, casas, terrenos\n"
                        "- Precios, ventas, inventarios\n"
                        "- Cualquier dato que esté en las bases de datos"
                    )
                )
            )
            logger.info("✓ Tool 'general' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando general: {e}")
            raise

        property_question_engine = PropertyQuestionEngine(
        property_db_service=self.property_db_service,
        context_manager=self.context_manager
        )



        QueryEngineTool(
        query_engine=property_question_engine,
        metadata=ToolMetadata(
            name="property_info",
            description=(
                "🏠 INFORMACIÓN ESPECÍFICA DE PROPIEDADES DESDE BASE DE DATOS\n\n"
                "USAR CUANDO el usuario pregunta detalles específicos sobre UNA propiedad:\n"
                "✅ 'a que banco pertenece?'\n"
                "✅ 'quien es el agente?'\n"
                "✅ 'cual es el precio?'\n"
                "✅ 'cuantas habitaciones tiene?'\n"
                "✅ 'donde está ubicada?'\n\n"
                "NO USAR para:\n"
                "❌ Búsquedas de múltiples propiedades\n"
                "❌ Descripciones detalladas completas\n\n"
                "Este tool responde RÁPIDO desde la base de datos sin necesidad de crawlear la web."
            ),
        ),
    ),

















        
        # -------- Tavily (Internet - solo bienesadjudicadoscr.com) --------
        try:
            tavily = TavilyBienesQueryEngine(api_key=settings.tavily_api_key, property_db_service=self.property_db_service)
            internet_tool = QueryEngineTool(
                query_engine=tavily,
                metadata=ToolMetadata(
                    name="internet_bienesadjudicadoscr",
                    description=(
                        "🌐 BÚSQUEDA EN SITIO WEB BIENESADJUDICADOSCR.COM\n\n"
                        "USAR SOLO CUANDO:\n"
                        "- Usuario proporciona un enlace específico de bienesadjudicadoscr.com\n"
                        "- Usuario menciona un código de propiedad específico del sitio\n"
                        "- Necesitas detalles que solo están en la página web pública\n\n"
                        "NO USAR para búsquedas generales de propiedades (usa 'bienes_adjudicados')\n"
                        "RESTRICCIÓN: Solo accede a URLs de bienesadjudicadoscr.com"
                    )
                ),
            )
            logger.info("✓ Tool 'internet_bienesadjudicadoscr' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando tavily: {e}")
            raise














        

        # -------- Router --------
        self.tools = [sql_db1_tool, sql_db2_tool, general_tool, internet_tool]
        self.router = RouterQueryEngine(
            selector=PydanticSingleSelector.from_defaults(),
            query_engine_tools=self.tools,
        )
        logger.info(f"✓ Router inicializado con {len(self.tools)} herramientas")

    # -------- Main API --------
    def query(self, user_query: str):
        """Ejecuta query con logging detallado"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📥 NUEVA CONSULTA: {user_query}")
        logger.info(f"{'='*60}")
        
        try:
            # El router internamente usa el selector para elegir el tool
            response = self.router.query(user_query)
            
            # Intentar extraer qué tool se usó
            selected_tool = "desconocido"
            if hasattr(response, 'metadata') and response.metadata:
                selected_tool = response.metadata.get('selector_result', 'desconocido')
            
            logger.info(f"🔧 Tool seleccionado: {selected_tool}")
            logger.info(f"📤 Respuesta generada (primeros 200 chars): {str(response)[:200]}...")
            
            return response
        except Exception as e:
            logger.error(f"❌ ERROR en query: {e}", exc_info=True)
            raise

    def is_tool_response(self, response) -> bool:
        """Detecta si la respuesta es una herramienta (QueryEngineTool) o texto plano."""
        return any(
            tool.metadata.name in str(response).lower() for tool in self.tools
        )
