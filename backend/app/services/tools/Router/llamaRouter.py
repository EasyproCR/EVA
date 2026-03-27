from __future__ import annotations
import logging
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.selectors import PydanticSingleSelector
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from app.services.tools.Router.SQLQuery.llamaSQLquery import LlamaSQLQuery
from app.services.tools.Router.SQLQuery.retrieverSql import RetrieverSQL, TableRetrieverConfig
from app.services.tools.Router.SQLQuery.bienesadjudicados import BienesAdjudicadosTool
from app.services.tools.Router.SQLQuery.bienesadjudicados.bienesqueryengine import BienesQueryEngine
from app.services.tools.Router.SQLQuery.bienesadjudicados.banksqueryengine import BanksQueryEngine
from app.services.tools.Router.SQLQuery.bienesadjudicados.propertydbservice import PropertyDatabaseService
from app.services.tools.Router.General.general_query_engine import GeneralQueryEngine
from app.services.tools.Router.General.tavilyService import TavilyBienesQueryEngine
from app.services.tools.Router.General.property_question_engine import PropertyQuestionEngine
from app.services.tools.Router.General.rrhh_question_engine import RrhhQuestionEngine
from app.services.tools.Router.General.posts_question_engine import PostsQuestionEngine
from app.services.tools.Router.General.posts_generation_engine import PostsGenerationEngine
from app.services.tools.Router.General.query_preprocessor import QueryPreprocessor, QueryType
from app.services.conversation_context import ConversationContext
from app.data import easycoreContext
from app.data.easycoreRoleAccess import build_role_scoped_catalog, normalize_roles
from app.services.tools.Router.InternetSearchEngine import InternetSearchEngine

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_conn_uri(settings, key: str) -> str:
    """Obtiene una URI de conexión desde settings."""
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
    """Router (LlamaIndex) para elegir entre herramientas de consulta."""

    def __init__(
        self,
        settings,
        db1_key: str = "DB_URI_BIENES",
        db2_key: str = "DB_URI_EASYCORE",
        context_manager=ConversationContext()
    ):
        self.settings = settings
        self.context_manager = context_manager
        self.property_db_service = PropertyDatabaseService(
            connection_uri=_get_conn_uri(settings, "DB_URI_BIENES")
        )
        self.query_preprocessor = QueryPreprocessor()
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
                        "USAR CUANDO el usuario hace BÚSQUEDAS o CONSULTAS GENERALES sobre:\n"
                        "- 'Casas en San José', 'terrenos en Guanacaste'\n"
                        "- Búsquedas por ubicación, precio, características\n"
                        "- 'Propiedades con 3 habitaciones', 'lotes en Escazú'\n"
                        "- 'Bienes adjudicados bajo 100k', 'remates bancarios'\n"
                        "- Listados de múltiples propiedades\n\n"
                        "NO USAR cuando el usuario pregunta por información ESPECÍFICA de UNA propiedad:\n"
                        "❌ '¿Cuál es el precio?' (sin especificar propiedad)\n"
                        "❌ '¿Quién es el agente?' (sin especificar propiedad)\n"
                        "❌ Para eso usa 'property_info' tool\n\n"
                        "NOTA: Usa este tool para LISTAR y BUSCAR, usa property_info para DETALLES"
                    ),
                )
            )
            logger.info("✓ Tool 'bienes_adjudicados' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando bienes_adjudicados: {e}")
            raise

        # -------- Banks tool (Búsqueda de bancos y sus propiedades) --------
        try:
            qe_banks = BanksQueryEngine(bienes_db)
            banks_tool = QueryEngineTool(
                query_engine=qe_banks,
                metadata=ToolMetadata(
                    name="bancos",
                    description=(
                        "🏦 BASE DE DATOS DE BANCOS Y SUS PROPIEDADES EN REMATE\n\n"
                        "USAR CUANDO el usuario pregunta sobre:\n"
                        "- Información de bancos específicos\n"
                        "- Propiedades en remate de un banco\n"
                        "- Comparación entre bancos\n"
                        "- Estadísticas de propiedades por banco\n"
                        "- Precios promedio por banco\n"
                        "- Tipos de propiedades que maneja cada banco\n\n"
                        "EJEMPLOS:\n"
                        "✅ 'qué propiedades tiene el Banco Nacional?'\n"
                        "✅ 'cuántas casas en remate del BCR?'\n"
                        "✅ 'precios promedio del Banco Popular'\n"
                        "✅ 'terrenos en remate del BCCR'\n\n"
                        "DATOS DISPONIBLES:\n"
                        "- Nombre del banco\n"
                        "- Total de propiedades\n"
                        "- Rango de precios (mín, máx, promedio)\n"
                        "- Tipos de propiedades\n"
                        "- Ubicación por provincias\n"
                        "- Detalles de propiedades específicas"
                    ),
                )
            )
            logger.info("✓ Tool 'bancos' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando bancos: {e}")
            raise

        # -------- SQL tool 2 (DB2 - Easycore) --------
        try:
            db2_uri = _get_conn_uri(settings, db2_key)
            self.db2_sql_db = LlamaSQLQuery(db2_uri).get_sql_database()
            self.easycore_base_catalog = easycoreContext.TABLE_CATALOG_EASYCORE
            self.easycore_tool_cache = {}

            sql_db2_tool = self._build_easycore_tool_for_roles(["administrator"])
            logger.info("✓ Tool 'easycore' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando easycore: {e}")
            raise

        # -------- General tool --------
        try:
            general_qe = GeneralQueryEngine()
            general_tool = QueryEngineTool(
                query_engine=general_qe,
                metadata=ToolMetadata(
                    name="general",
                    description=(
                        "💬 CONVERSACIÓN GENERAL Y CONOCIMIENTO GENERAL\n\n"
                        "USAR CUANDO:\n"
                        "- Usuario saluda: 'hola', 'buenos días', '¿qué tal?'\n"
                        "- Preguntas de cortesía: '¿Cuál es tu nombre?', '¿Qué puedes hacer?'\n"
                        "- Preguntas de CONOCIMIENTO GENERAL:\n"
                        "  ✅ '¿Qué es un bien raíz?'\n"
                        "  ✅ '¿Qué significa adjudicado?'\n"
                        "  ✅ '¿Cuál es la capital de Costa Rica?'\n"
                        "  ✅ 'Explícame sobre préstamos hipotecarios'\n"
                        "- Cualquier pregunta que NO requiera datos específicos de la BD\n\n"
                        "NO USAR si el usuario pide:\n"
                        "❌ Propiedades específicas con ID/nombre (usa property_info)\n"
                        "❌ Búsquedas de propiedades (usa bienes_adjudicados)\n"
                        "❌ Información de personas/usuarios (usa easycore)\n\n"
                        "NOTA: Este tool responde con CONOCIMIENTO GENERAL, no con datos de BD"
                    )
                )
            )
            logger.info("✓ Tool 'general' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando general: {e}")
            raise

        # -------- Property Info tool --------
        try:
            property_question_engine = PropertyQuestionEngine(
                property_db_service=self.property_db_service,
                context_manager=self.context_manager
            )
            # Guardar referencia al engine para uso en pre-procesador
            self.property_question_engine = property_question_engine

            property_info_tool = QueryEngineTool(
                query_engine=property_question_engine,
                metadata=ToolMetadata(
                    name="property_info",
                    description=(
                        "🏠 INFORMACIÓN ESPECÍFICA DE PROPIEDADES DESDE BASE DE DATOS\n\n"
                        "USAR CUANDO el usuario pregunta por DETALLES ESPECÍFICOS de UNA propiedad:\n\n"
                        "CON ID/NOMBRE EXPLÍCITO:\n"
                        "✅ '¿Cuál es el precio de la propiedad 150?'\n"
                        "✅ '¿Quién es el agente del terreno en Moravia?'\n"
                        "✅ '¿A qué banco pertenece la propiedad 16467?'\n"
                        "✅ '¿Dónde está ubicada la casa en Escazú?'\n\n"
                        "CON CONTEXTO (de pregunta anterior):\n"
                        "✅ Usuario: 'Info de propiedad 150'\n"
                        "✅ Usuario: '¿Cuál es el precio?' (recuerda propiedad 150)\n"
                        "✅ Usuario: '¿Quién es el agente?' (recuerda contexto)\n\n"
                        "RESPONDE A:\n"
                        "- Precio de la propiedad\n"
                        "- Agente/contacto\n"
                        "- Banco/Entidad\n"
                        "- Ubicación (distrito, cantón, provincia)\n"
                        "- Tipo de propiedad\n"
                        "- Características (habitaciones, baños, área)\n\n"
                        "NO USAR para:\n"
                        "❌ Búsquedas de múltiples propiedades\n"
                        "❌ 'Casas baratas en San José' (usa bienes_adjudicados)"
                    ),
                ),
            )
            self.property_info_tool = property_info_tool
            logger.info("✓ Tool 'property_info' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando property_info: {e}")
            raise

        # -------- RRHH Question Engine (Control de acceso para recursos humanos) --------
        try:
            rrhh_engine = RrhhQuestionEngine(sql_database=self.db2_sql_db)
            rrhh_tool = QueryEngineTool(
                query_engine=rrhh_engine,
                metadata=ToolMetadata(
                    name="rrhh_info",
                    description=(
                        "👥 INFORMACIÓN DE RECURSOS HUMANOS (CONTROL DE ACCESO)\n\n"
                        "USAR CUANDO el usuario pregunta sobre:\n"
                        "- Expedientes de empleados\n"
                        "- Vacaciones, permisos y licencias\n"
                        "- Solicitudes de crédito/préstamo\n"
                        "- Pautas y políticas internas\n"
                        "- Recordatorios administrativos\n\n"
                        "EJEMPLOS:\n"
                        "✅ '¿Cuál es el expediente de Juan?'\n"
                        "✅ '¿Cuántos días de vacaciones tiene María?'\n"
                        "✅ '¿Estado de solicitud de crédito de Carlos?'\n"
                        "✅ '¿Cuál es la política de...?'\n\n"
                        "NOTA: Solo usuarios con rol 'rrhh' o 'super_admin' pueden acceder.\n"
                        "Otros usuarios recibirán mensaje indicando que contacten al área de RRHH."
                    ),
                ),
            )
            self.rrhh_engine = rrhh_engine
            self.rrhh_tool = rrhh_tool
            logger.info("✓ Tool 'rrhh_info' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando rrhh_info: {e}")
            raise

        # -------- Posts Question Engine (Control de acceso para publicaciones en redes sociales) --------
        try:
            posts_engine = PostsQuestionEngine(sql_database=self.db2_sql_db)
            posts_tool = QueryEngineTool(
                query_engine=posts_engine,
                metadata=ToolMetadata(
                    name="posts_info",
                    description=(
                        "📱 INFORMACIÓN DE POSTS/PUBLICACIONES EN REDES SOCIALES\n\n"
                        "USAR CUANDO el usuario pregunta sobre:\n"
                        "- Posts en Instagram, Facebook, Twitter, TikTok, LinkedIn, YouTube\n"
                        "- Estadísticas de engagement (reacciones, comentarios, shares, vistas)\n"
                        "- Publicaciones por plataforma\n"
                        "- Top posts con mejor rendimiento\n"
                        "- Campañas sociales y contenido publicado\n\n"
                        "EJEMPLOS:\n"
                        "✅ '¿Cuáles son los posts en Instagram?'\n"
                        "✅ '¿Cuál es el post con más reacciones?'\n"
                        "✅ '¿Estadísticas de los posts de Facebook?'\n"
                        "✅ '¿Posts con mejor engagement?'\n"
                        "✅ 'Muestra los posts más compartidos'\n\n"
                        "ACCESO: Abierto para TODOS los usuarios.\n"
                        "Los datos vienen de la base de datos de campañas sociales, NO de internet."
                    ),
                ),
            )
            self.posts_engine = posts_engine
            self.posts_tool = posts_tool
            logger.info("✓ Tool 'posts_info' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando posts_info: {e}")
            raise

        # -------- Posts Generation Engine (Generar contenido de posts para todos) --------
        try:
            posts_gen_engine = PostsGenerationEngine(sql_database=self.db2_sql_db)
            posts_gen_tool = QueryEngineTool(
                query_engine=posts_gen_engine,
                metadata=ToolMetadata(
                    name="posts_generation",
                    description=(
                        "✍️ GENERACIÓN DE POSTS/CONTENIDO PARA REDES SOCIALES\n\n"
                        "USAR CUANDO el usuario pide:\n"
                        "- Elaborar/generar/crear un post\n"
                        "- Escribir contenido para Instagram, Facebook, Twitter, TikTok, LinkedIn, YouTube\n"
                        "- Ideas de posts para una propiedad/producto/noticia\n"
                        "- Captions o textos para publicaciones\n"
                        "- Contenido optimizado para redes sociales\n\n"
                        "EJEMPLOS:\n"
                        "✅ 'Elabora un post de esta propiedad'\n"
                        "✅ 'Genera un tweet sobre nuestro producto'\n"
                        "✅ 'Crea un caption para Instagram'\n"
                        "✅ 'Escribe un post informativo para LinkedIn'\n"
                        "✅ 'Haz un video script para TikTok'\n\n"
                        "ACCESO: Abierto para TODOS los usuarios sin restricciones de rol.\n"
                        "NOTA: Utiliza IA para crear contenido optimizado por plataforma."
                    ),
                ),
            )
            self.posts_gen_engine = posts_gen_engine
            self.posts_gen_tool = posts_gen_tool
            logger.info("✓ Tool 'posts_generation' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando posts_generation: {e}")
            raise

        try:
            tavily = TavilyBienesQueryEngine(
                api_key=settings.tavily_api_key,
                property_db_service=self.property_db_service
            )
            internet_tool = QueryEngineTool(
                query_engine=tavily,
                metadata=ToolMetadata(
                    name="internet_bienesadjudicadoscr",
                    description=(
                        "🌐 BÚSQUEDA EN SITIO WEB BIENESADJUDICADOSCR.COM\n\n"
                        "USAR SOLO CUANDO:\n"
                        "- Usuario proporciona un enlace específico de bienesadjudicadoscr.com\n"
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

# -------- Búsqueda general en internet --------
        try:
            internet_search_qe = InternetSearchEngine(api_key=settings.tavily_api_key)
            internet_search_tool = QueryEngineTool(
                query_engine=internet_search_qe,
                metadata=ToolMetadata(
                    name="internet_search",
                    description=(
                        "🔍 BÚSQUEDA GENERAL EN INTERNET\n\n"
                        "USAR CUANDO el usuario pide buscar cualquier cosa en internet:\n"
                        "✅ 'busca en internet...'\n"
                        "✅ 'qué dice internet sobre...'\n"
                        "✅ Noticias, eventos recientes, precios de mercado\n"
                        "✅ Cualquier pregunta de conocimiento general o actualidad\n\n"
                        "NO USAR para:\n"
                        "❌ Propiedades de bienesadjudicadoscr.com\n"
                        "❌ Datos que ya están en EasyCore o Bienes Adjudicados"
                    )
                ),
            )
            logger.info("✓ Tool 'internet_search' configurado correctamente")
        except Exception as e:
            logger.error(f"✗ Error configurando internet_search: {e}")
            raise

        # -------- Router --------
        self.base_tools = [sql_db1_tool, banks_tool, rrhh_tool, posts_tool, posts_gen_tool, general_tool, property_info_tool, internet_tool, internet_search_tool]
        self.default_tools = [*self.base_tools, sql_db2_tool]
        self.router = RouterQueryEngine(
            selector=PydanticSingleSelector.from_defaults(),
            query_engine_tools=self.default_tools,
        )
        logger.info(f"✓ Router inicializado con {len(self.default_tools)} herramientas")

    def _easycore_tool_description(self, allowed_tables: list[str]) -> str:
        return (
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
            "IMPORTANTE: Para nombres de personas, usa LIKE parcial, no igualdad exacta.\n"
            f"TABLAS PERMITIDAS PARA ESTE ROL: {', '.join(allowed_tables) if allowed_tables else 'ninguna'}"
        )

    def _build_easycore_tool_for_roles(self, user_roles: list[str] | None) -> QueryEngineTool:
        scoped_catalog = build_role_scoped_catalog(self.easycore_base_catalog, user_roles)
        cache_key = "|".join(sorted(scoped_catalog.keys()))

        if cache_key in self.easycore_tool_cache:
            return self.easycore_tool_cache[cache_key]

        db2_engine = RetrieverSQL(
            self.db2_sql_db,
            table_catalog=scoped_catalog,
            config=TableRetrieverConfig(similarity_top_k=6),
        ).get_query_engine()

        tool = QueryEngineTool(
            query_engine=db2_engine,
            metadata=ToolMetadata(
                name="easycore",
                description=self._easycore_tool_description(sorted(scoped_catalog.keys())),
            ),
        )

        self.easycore_tool_cache[cache_key] = tool
        return tool

    def _tools_for_roles(self, user_roles: list[str] | None):
        scoped_easycore_tool = self._build_easycore_tool_for_roles(user_roles)
        return [*self.base_tools, scoped_easycore_tool]

    # -------- Main API --------
    def query(self, user_query: str, session_id: str = None, user_roles: list[str] | None = None):
        """
        Ejecuta query con pre-procesamiento inteligente.

        1. Pre-procesa la consulta para detectar patrones específicos (ej: IDs de propiedades)
        2. Si detecta un patrón, enruta DIRECTAMENTE a la herramienta específica
        3. Si no detecta patrón, usa el router LLaMA normal
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📥 NUEVA CONSULTA: {user_query}")
        logger.info(f"👤 Roles usuario: {sorted(normalize_roles(user_roles or []))}")
        logger.info(f"{'='*60}")

        try:
            # 1️⃣ PRE-PROCESAMIENTO: Detectar patrones específicos
            query_type, property_id = self.query_preprocessor.analyze(user_query)

            # Establecer user_roles en engines especializados
            self.rrhh_engine.set_user_roles(user_roles)
            self.posts_engine.set_user_roles(user_roles)

            # 2️⃣ Si detectó ID de propiedad, ENRUTA DIRECTO a property_info
            if query_type == QueryType.PROPERTY_ID:
                logger.info(f"🎯 ENRUTAMIENTO DIRECTO: Property ID #{property_id}")
                from llama_index.core.schema import QueryBundle
                query_bundle = QueryBundle(query_str=user_query)
                # Pasar session_id al engine si está disponible
                if session_id:
                    self.property_question_engine.session_id = session_id
                response = self.property_question_engine._query(query_bundle)
                logger.info(f"🔧 Tool seleccionado: property_info (directo por ID)")
                logger.info(f"📤 Respuesta generada (primeros 200 chars): {str(response)[:200]}...")
                return response

            # 3️⃣ Si NO detectó patrón, usa ROUTER NORMAL (LLaMA selector)
            logger.info(f"🚀 ENRUTAMIENTO NORMAL: Pasando al router LLaMA...")
            # Asignar session_id al engine para contexto
            if session_id:
                self.property_question_engine.session_id = session_id
            role_router = RouterQueryEngine(
                selector=PydanticSingleSelector.from_defaults(),
                query_engine_tools=self._tools_for_roles(user_roles),
            )
            response = role_router.query(user_query)

            selected_tool = "desconocido"
            if hasattr(response, 'metadata') and response.metadata:
                selected_tool = response.metadata.get('selector_result', 'desconocido')

            logger.info(f"🔧 Tool seleccionado: {selected_tool}")
            logger.info(f"📤 Respuesta generada (primeros 200 chars): {str(response)[:200]}...")

            return response
        except Exception as e:
            logger.error(f"❌ ERROR en query: {e}", exc_info=True)
            raise

    def is_tool_response(self, response_text: str) -> bool:
        """Detecta si la respuesta proviene de una tool de datos. Recibe el string ya convertido."""
        try:
            response_lower = response_text.lower()
            if not hasattr(self, 'default_tools'):
                logger.error("❌ ERROR: self.default_tools no existe. Atributos del router: %s", dir(self))
                return False
            return any(
                tool.metadata.name in response_lower for tool in self.default_tools
                if tool.metadata.name != "general"
            )
        except Exception as e:
            logger.error(f"❌ ERROR en is_tool_response: {e}", exc_info=True)
            return False
    
