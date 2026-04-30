import sys
import asyncio
sys.path.append('c:\\laragon\\www\\easycore-eva\\eva\\backend')
from app.services.llamaOrchestor import LlamaOrchestor
from app.core.config import get_settings

async def test():
    settings = get_settings()
    orchestrator = LlamaOrchestor(settings)
    
    response = await orchestrator.process_message(
        query="EVA hay solicitudes de Credid pendientes?",
        user_id=1,
        user_roles=["master"]
    )
    print("RESPONSE:", response)

asyncio.run(test())
