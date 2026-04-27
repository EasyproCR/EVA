import logging
from app.core.config import get_settings
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings
from app.services.tools.Router import llamaRouter
from app.data import evaPrompt
from llama_index.embeddings.openai.base import OpenAIEmbedding
from llama_index.core.memory import Memory
from llama_index.core.llms import ChatMessage
from app.services.property_detector import detect_property_reference
from app.services.conversation_context import expand_contextual_question

logger = logging.getLogger(__name__)

class LlamaOrchestor:
    def __init__(self, settings):
        self.settings = settings
        
        
        Settings.llm= OpenAI(
            api_key=self.settings.openai_api_key,
            model=self.settings.openai_model,
            max_tokens=self.settings.openai_max_tokens,
            temperature=0.1,
            timeout=120.0,
            system_prompt=(
                "Responde en español. Tienes acceso a bases de datos como Easycore y Bienes Adjudicados y a un servicio externo de internet. "
                "Elige la herramienta adecuada según la consulta del usuario. "
                "Cuando proporciones información o listados de propiedades, debes incluir explícitamente a qué banco pertenecen. "
                "Si el usuario te solicita redactar o hacer posts/publicaciones para redes sociales, utiliza la herramienta posts_generation. "
                "Si el usuario pregunta específicamente por bancos, estadísticas de bancos o propiedades de un banco, utiliza la herramienta bancos. "
                "Cuando generes consultas SQL para buscar personas por nombre, utiliza LIKE en vez de igualdad exacta. "
                "Por ejemplo: WHERE nombre LIKE '%Silvia%' en vez de WHERE nombre = 'Silvia'. "
                "Haz la búsqueda insensible a mayúsculas y busca tanto en nombre como en apellido. "
                "Si el usuario da solo el nombre, busca coincidencias parciales en nombre y apellido. "
            )
        )

        self.idUsuario= None


        Settings.embed_model = OpenAIEmbedding(
            api_key=self.settings.openai_api_key,
            timeout=120.0
        )
        self.router = llamaRouter.LlamaRouter(settings)

        self.memories = {}  # session_id -> Memory
        
    def _mem(self, session_id: str) -> Memory:
        if session_id not in self.memories:
            self.memories[session_id] = Memory.from_defaults(
                session_id=session_id,
                token_limit=20000
            )
        self.idUsuario = session_id
    
        return self.memories[self.idUsuario]

    def procesar_mensaje(self, mensaje: str , session_id: str, nombreUsuario: str, user_roles: list[str] | None = None) -> str:
        """
        Procesa un mensaje usando routing + memoria por sesión.

        - Router decide usando SOLO el mensaje actual.
        - Memoria se usa cuando el usuario hace referencias contextuales.
        - Guarda user + assistant en memoria.
        """

        # Actualizar system prompt dinámicamente con el nombre del usuario
        user_context = f"Estás conversando con {nombreUsuario}. " if nombreUsuario else "Estás conversando con el usuario. "
        dynamic_system_prompt = (
            f"{user_context}"
            "Responde en español. Tienes acceso a bases de datos como Easycore y Bienes Adjudicados y a un servicio externo de internet. "
            "Elige la herramienta adecuada según la consulta del usuario. "
            "Cuando proporciones información o listados de propiedades, debes incluir explícitamente a qué banco pertenecen. "
            "Si el usuario te solicita redactar o hacer posts/publicaciones para redes sociales, utiliza la herramienta posts_generation. "
            "Si el usuario pregunta específicamente por bancos, estadísticas de bancos o propiedades de un banco, utiliza la herramienta bancos. "
            "Cuando generes consultas SQL para buscar personas por nombre, utiliza LIKE en vez de igualdad exacta. "
            "Por ejemplo: WHERE nombre LIKE '%Silvia%' en vez de WHERE nombre = 'Silvia'. "
            "Haz la búsqueda insensible a mayúsculas y busca tanto en nombre como en apellido. "
            "Si el usuario da solo el nombre, busca coincidencias parciales en nombre y apellido. "
        )
        Settings.llm = OpenAI(
            api_key=self.settings.openai_api_key,
            model=self.settings.openai_model,
            max_tokens=self.settings.openai_max_tokens,
            temperature=0.1,
            timeout=120.0,
            system_prompt=dynamic_system_prompt
        )

        # Obtener memoria de la sesión
        mem = self._mem(session_id)

        # Recuperar historial relevante
        chat_history = mem.get(input=mensaje) or []

        # Tomar últimos turnos para contexto (evita prompts gigantes)
        last = chat_history[-10:]


        mensaje = detect_property_reference(mensaje, last)
        mensaje = expand_contextual_question(mensaje, session_id)
        # Detectar si el usuario está haciendo referencia contextual
        ref_words = (
            "antes", "anterior", "eso", "lo anterior",
            "qué te dije", "que te dije", "lo de arriba",
            "como dijiste", "como habíamos"
        )

        usar_historial = any(w in mensaje.lower() for w in ref_words)

        # Routing (selector decide tool)
        query_text = mensaje if not usar_historial else "\n".join([f"{h.role}: {h.content}" for h in last]) + "\nUsuario: " + mensaje
        raw = self.router.query(query_text, session_id=session_id, user_roles=user_roles or [])

        resp = raw.response if hasattr(raw, "response") else raw
        
        # seguridad: si por alguna razón llega bytes
        if isinstance(resp, (bytes, bytearray)):
            resp = resp.decode("utf-8", errors="replace")

        resp = str(resp)

        # Guardar en memoria (si no es tool)
        if not self.router.is_tool_response(resp):
            mem.put_messages([
                ChatMessage(role="user", content=f"{nombreUsuario}: {mensaje}"),
                ChatMessage(role="assistant", content=resp),
            ])
        return resp
    
    def obtenerIDUsuario(self):
        return self.idUsuario

    def get_rrhh_reminders(self, user_roles: list[str]) -> dict:
        """
        Obtiene recordatorios pendientes de RRHH si el usuario tiene permiso.

        Args:
            user_roles: Lista de roles del usuario

        Returns:
            dict con recordatorios o mensaje de no autorizado
        """
        # Verificar si tiene rol de RRHH
        allowed_roles = {'super_admin', 'rrhh'}
        roles_lower = [str(r).lower().strip() for r in user_roles]

        if not any(role in allowed_roles for role in roles_lower):
            return {"authorized": False, "count": 0, "reminders": []}

        # Obtener recordatorios desde el rrhh_engine.data_service
        try:
            if hasattr(self.router, 'rrhh_engine') and self.router.rrhh_engine:
                data_service = self.router.rrhh_engine.data_service
                if data_service:
                    result = data_service.get_pending_reminders_for_greeting()
                    result["authorized"] = True
                    return result
            return {"authorized": True, "count": 0, "reminders": [], "error": "Servicio no disponible"}
        except Exception as e:
            return {"authorized": True, "count": 0, "reminders": [], "error": str(e)}

    def get_operations_reminders(self, user_id: int, user_roles: list[str]) -> dict:
        """
        Obtiene recordatorios pendientes de Operations si el usuario tiene permiso.
        Para Alejandra: muestra citas pendientes en el saludo inicial.

        Args:
            user_id: ID del usuario autenticado
            user_roles: Lista de roles del usuario

        Returns:
            dict con recordatorios o mensaje de no autorizado
        """
        # Verificar si tiene rol de operations
        allowed_roles = {'super_admin', 'operations'}
        roles_lower = [str(r).lower().strip() for r in user_roles]

        if not any(role in allowed_roles for role in roles_lower):
            return {"authorized": False, "count": 0, "reminders": []}

        # Obtener recordatorios desde el operations_engine.data_service
        try:
            if hasattr(self.router, 'operations_engine') and self.router.operations_engine:
                data_service = self.router.operations_engine.data_service
                if data_service:
                    result = data_service.get_pending_reminders_for_greeting(user_id)
                    result["authorized"] = True
                    return result
            return {"authorized": True, "count": 0, "reminders": [], "error": "Servicio no disponible"}
        except Exception as e:
            return {"authorized": True, "count": 0, "reminders": [], "error": str(e)}

    def get_customer_reminders(self, user_id: int = None) -> dict:
        """
        Obtiene recordatorios de clientes para el saludo inicial.

        Args:
            user_id: ID del usuario autenticado

        Returns:
            dict con recordatorios de clientes o mensaje de no autorizado
        """
        # Acceso abierto para todos los usuarios autenticados
        if not user_id:
            return {"authorized": False, "count": 0, "reminders": []}

        # Obtener recordatorios desde el customer_reminders_engine.data_service
        try:
            if hasattr(self.router, 'customer_reminders_engine') and self.router.customer_reminders_engine:
                data_service = self.router.customer_reminders_engine.data_service
                if data_service:
                    result = data_service.get_pending_reminders_for_greeting(user_id)
                    result["authorized"] = True
                    return result
            return {"authorized": True, "count": 0, "reminders": [], "error": "Servicio no disponible"}
        except Exception as e:
            return {"authorized": True, "count": 0, "reminders": [], "error": str(e)}