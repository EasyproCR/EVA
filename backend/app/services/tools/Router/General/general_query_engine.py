from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.base.response.schema import Response
from llama_index.core.prompts import PromptTemplate
from llama_index.core import Settings

GENERAL_PROMPT = PromptTemplate(
    "Eres EVA, un asistente útil y breve.\n"
    "Si el usuario saluda, saluda y pregunta qué necesita.\n"
    "Si el usuario pide algo general (sin datos ni documentos), responde directo.\n"
    "Si el usuario pide datos específicos (DB/documentos), dile que lo especifique.\n\n"
    "Usuario: {q}\n"
    "Respuesta:"
)

class GeneralQueryEngine(CustomQueryEngine):
    def custom_query(self, query_str: str) -> Response:
        llm = Settings.llm
        txt = llm.complete(GENERAL_PROMPT.format(q=query_str)).text
        return Response(response=txt)
