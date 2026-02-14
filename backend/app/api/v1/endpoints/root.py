from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest
from app.services.easycore_auth import EasycoreAuth

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Main health check endpoint."""
    return {"status": "ok", "app": "EVA"}


@router.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {"message": "Welcome to EVA API v1"}


@router.post("/saludo")
async def saludo(request: ChatRequest) -> dict:
    """Simple greeting endpoint."""
    body = {
        "id": request.id,
        "nombre": request.nombre,
        "mensaje": request.mensaje,
    }
    
    validation = EasycoreAuth.from_chat_body(body)
    
    if not validation["ok"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    validated_data = validation["value"]
    
    return {"message": f"Hola {validated_data['nombre']}! Soy EVA, tu asistente de IA. En qué puedo ayudarte hoy?"}
