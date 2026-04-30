import sys
import logging
sys.path.append('c:\\laragon\\www\\easycore-eva\\eva\\backend')
logging.basicConfig(level=logging.INFO)

from app.core.config import get_settings
from app.services.tools.Router.llamaRouter import LlamaRouter
from app.services.llamaOrchestor import LlamaOrchestor

settings = get_settings()
orchestor = LlamaOrchestor(settings)

prompt = "Eva puedes decirme si hay credid pendientes de hacer"
print(f"QUERY: {prompt}")
res = orchestor.procesar_mensaje(prompt, session_id="test", nombreUsuario="Admin", user_roles=["super_admin"])
print("\nFINAL RESULT:\n=============================")
print(res)
