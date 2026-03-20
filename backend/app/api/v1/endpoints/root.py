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
    nombre = request.nombre if hasattr(request, 'nombre') and request.nombre else ""
    if nombre:
        return {"message": f"Hola {nombre}! Soy EVA, tu asistente de IA. ¿En qué puedo ayudarte hoy?"}
    return {"message": "Hola! Soy EVA, tu asistente de IA. ¿En qué puedo ayudarte hoy?"}
