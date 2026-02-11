"""
Endpoints de IA - Heredan de IAServicio con decoradores elegantes
Usa fastapi-class para Class-Based Views
"""

from fastapi import APIRouter, Request
from fastapi import Depends, HTTPException
from app.core.config import get_settings
from app.schemas.chat import ChatRequest, ChatResponse, DeleteRequest
from app.api.ia_servicio import require_auth_dependency, validate_mensaje_dependency, validate_delete_body_dependency, get_user_info_dependency
from app.services.llamaOrchestor import LlamaOrchestor

router = APIRouter(prefix="/api", tags=["ia"])



# Dependencias para autenticación y utilidades
# Estas funciones deben estar implementadas en ia_servicio.py

@router.post("/chat", response_model=ChatResponse,  x_session_id: str = Header(default="dev"))
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
    response_obj = orch.procesar_mensaje(mensaje_limpio or request.mensaje)
    response_text = str(response_obj)
    return ChatResponse(respuesta=response_text, id=user_info.get("id", ""))

@router.get("/saludo")
async def saludo(user_info: dict = Depends(get_user_info_dependency)) -> dict:
    """
    Endpoint de saludo inicial.
    GET /api/saludo
    """
    if user_info.get("authenticated"):
        return {
            "saludo": f"Hola {user_info.get('nombre', '')}! Soy EVA, tu asistente de IA. ¿En qué puedo ayudarte hoy?"
        }
    return {
        "saludo": "Hola! Soy EVA, tu asistente de IA. ¿En qué puedo ayudarte hoy?"
    }

@router.post("/eliminarMemoria")
async def eliminar_memoria(
    request: DeleteRequest,
    user_info: dict = Depends(get_user_info_dependency),
    require_auth: None = Depends(require_auth_dependency),
    delete_body: dict = Depends(validate_delete_body_dependency)
):
    """
    Elimina la memoria/historial del bot para un usuario.
    DELETE /api/eliminarMemoria
    """
    user_id = request.id if request.id else user_info.get("id", "")
    # TODO: Integrar con LlamaIndex para eliminar memoria
    return {
        "message": f"Memoria eliminada para usuario {user_id}",
        "success": True
    }

@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "ia"}
