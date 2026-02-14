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

class LlamaOrchestor:
    def __init__(self, settings):
        self.settings = settings
        
        
        Settings.llm= OpenAI( 
            api_key=self.settings.openai_api_key, 
            model=self.settings.openai_model, 
            max_tokens=self.settings.openai_max_tokens, 
            temperature=0.1,
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

        # Detectar si el usuario está haciendo referencia contextual
        ref_words = (
            "antes", "anterior", "eso", "lo anterior",
            "qué te dije", "que te dije", "lo de arriba",
            "como dijiste", "como habíamos"
        )

        usar_historial = any(w in mensaje.lower() for w in ref_words)

        # Construir input para router
        if usar_historial and last:
            transcript = "\n".join(
                [f"{m.role}: {m.content}" for m in last]
            )
            router_input = f"{transcript}\nuser: {mensaje}"
        else:
            router_input = mensaje

        # Routing (selector decide tool)
        raw = self.router.query(router_input)

        # Extraer respuesta
        resp = raw.response if hasattr(raw, "response") else str(raw)

        # Guardar conversación en memoria
        mem.put_messages([
            ChatMessage(role="user", content=f"{nombreUsuario}: {mensaje}"),
            ChatMessage(role="assistant", content=resp),
        ])

        return resp

    def obtenerIDUsuario(self):
        return self.idUsuario
