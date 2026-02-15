"""
Endpoints de IA - Heredan de IAServicio con decoradores elegantes
Usa fastapi-class para Class-Based Views
"""

from fastapi import APIRouter, Request, logger
from fastapi import Depends, HTTPException
from app.core.config import get_settings
from app.schemas.chat import ChatRequest, ChatResponse, DeleteRequest
from app.api.ia_servicio import require_auth_dependency, validate_mensaje_dependency, validate_delete_body_dependency, get_user_info_dependency
from app.services.llamaOrchestor import LlamaOrchestor

router = APIRouter(prefix="/api", tags=["ia"])



# Dependencias para autenticación y utilidades
# Estas funciones deben estar implementadas en ia_servicio.py

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_req: Request,
    user_info: dict = Depends(get_user_info_dependency),
    require_auth: None = Depends(require_auth_dependency),
    mensaje_limpio: str = Depends(validate_mensaje_dependency)
):
    """
    Endpoint principal de chat con el agente IA.
    POST /api/chat
    """
    settings = get_settings()
    orch = http_req.app.state.orch 
 
    print(f"[DEBUG] user_info id: {user_info.get('id', '')}")
    response_obj = orch.procesar_mensaje(mensaje_limpio or request.mensaje , session_id=user_info.get("id", ""), nombreUsuario=user_info.get("nombre", ""))
    response_text = str(response_obj)
    return ChatResponse(respuesta=response_text, id=user_info.get("id", ""))

@router.get("/saludo")
async def saludo(user_info: dict = Depends(get_user_info_dependency)) -> dict:
    """
    Endpoint de saludo inicial.
    GET /api/saludo
    """
    if  user_info.get("authenticated"):
        return {
            "saludo": f"Hola {user_info.get('nombre', '')}! Soy EVA, tu asistente de IA. ¿En qué puedo ayudarte hoy?"
        }
    return {
        "saludo": "Hola! Soy EVA, tu asistente de IA. ¿En qué puedo ayudarte hoy?"
    }

@router.delete("/eliminarMemoria")  # ✅ Cambiar a DELETE (o dejar POST)
async def eliminar_memoria(
    http_req: Request,  # ✅ Para acceder al orchestrator
    user_info: dict = Depends(get_user_info_dependency),
    require_auth: None = Depends(require_auth_dependency),
    # ✅ SIN request, SIN delete_body
):
    """
    Elimina la memoria del chat para el usuario autenticado.
    Usuario identificado por JWT - sin body.
    """
    
    # ✅ Usuario del token (no del body que no existe)
    user_id = user_info.get("id")
    
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Usuario no identificado"
        )
    
    # ✅ Obtener orchestrator
    orch = http_req.app.state.orch
    
    # ✅ REALMENTE eliminar la memoria
    memoria_existia = user_id in orch.memories
    
    if memoria_existia:
        del orch.memories[user_id]  # ← ESTO ES LO IMPORTANTE
        
        # Si tienes memory_timestamps del cleanup
        if hasattr(orch, 'memory_timestamps') and user_id in orch.memory_timestamps:
            del orch.memory_timestamps[user_id]
        
        logger.info(f"Memoria eliminada para usuario: {user_id}")
    
    return {
        "message": "Memoria eliminada exitosamente" if memoria_existia else "No había memoria",
        "success": True,
        "user_id": user_id,
        "deleted": memoria_existia  # Info útil
    }

@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "ia"}
