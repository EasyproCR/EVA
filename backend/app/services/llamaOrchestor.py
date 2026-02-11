from urllib import response
import openai 
from app.core.config import get_settings
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings 
from app.services.tools.Router import llamaRouter
from app.data import evaPrompt
from llama_index.embeddings.openai.base import OpenAIEmbedding

class LlamaOrchestor:
    """
    Orquestador para manejar la lógica de interacción con LLaMA.
    """

    def __init__(self, settings):
        self.settings = settings
        Settings.llm= OpenAI(
            api_key=self.settings.openai_api_key,
            model=self.settings.openai_model,
            max_tokens=self.settings.openai_max_tokens,
            temperature=0.1,
            system_prompt= evaPrompt.Prompt
        )

        Settings.embed_model = OpenAIEmbedding(
            api_key=self.settings.openai_api_key
        )
        self.router = llamaRouter.LlamaRouter(settings)

    def procesar_mensaje(self, mensaje: str) -> str:
        """
        Procesa el mensaje utilizando LLaMA y llamarouter quien indica a que tool ira la pregunta y este  devuelve una respuesta.
        """
        raw= self.router.query(mensaje)
        if hasattr(raw, "response"):
            return raw.response

        return str(raw)