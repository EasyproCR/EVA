from urllib import response
import openai 
from app.core.config import get_settings
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings 
from app.services.tools.Router import llamaRouter
from app.data import evaPrompt
from llama_index.embeddings.openai.base import OpenAIEmbedding
from llama_index.core.memory import Memory
from llama_index.core.llms import ChatMessage
import uuid
import logging
import uuid
from app.services.property_detector import detect_property_reference  # ✅ NUEVA
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
            system_prompt=(
                "Responde en español. Tienes acceso a bases de datos como Easycore y Bienes Adjudicados y a un servicio externo de internet. "
                "Elige la herramienta adecuada según la consulta del usuario. "
                "Cuando generes consultas SQL para buscar personas por nombre, utiliza LIKE en vez de igualdad exacta. "
                "Por ejemplo: WHERE nombre LIKE '%Silvia%' en vez de WHERE nombre = 'Silvia'. "
                "Haz la búsqueda insensible a mayúsculas y busca tanto en nombre como en apellido. "
                "Si el usuario da solo el nombre, busca coincidencias parciales en nombre y apellido. "
            )
        )

        self.idUsuario= None


        Settings.embed_model = OpenAIEmbedding(
            api_key=self.settings.openai_api_key
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

    def procesar_mensaje(self, mensaje: str , session_id: str, nombreUsuario: str) -> str:
        """
        Procesa un mensaje usando routing + memoria por sesión.

        - Router decide usando SOLO el mensaje actual.
        - Memoria se usa cuando el usuario hace referencias contextuales.
        - Guarda user + assistant en memoria.
        """

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
        raw = self.router.query(mensaje if not usar_historial else "\n".join([f"{h.role}: {h.content}" for h in last]) + "\nUsuario: " + mensaje)

        resp = raw.response if hasattr(raw, "response") else raw
        
        # seguridad: si por alguna razón llega bytes
        if isinstance(resp, (bytes, bytearray)):
            resp = resp.decode("utf-8", errors="replace")

        resp = str(resp)

        # Guardar en memoria (si no es tool)
        if not self.router.is_tool_response(raw):
            mem.put_messages([
            ChatMessage(role="user", content=f"{nombreUsuario}: {mensaje}"),
            ChatMessage(role="assistant", content=resp),
        ])

        print("RAW TYPE:", type(raw))
        print("RAW.RESPONSE TYPE:", type(getattr(raw, "response", None)))
        print("RAW.RESPONSE REPR:", repr(getattr(raw, "response", None))[:300])

        return resp
            

    def obtenerIDUsuario(self):
        return self.idUsuario
