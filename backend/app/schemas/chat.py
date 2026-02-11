from pydantic import BaseModel

class ChatRequest(BaseModel):
    """Chat request schema - solo mensaje, id/nombre vienen del token."""
    mensaje: str


class ChatResponse(BaseModel):
    """Chat response schema."""
    respuesta: str
    id: str | None = None


class DeleteRequest(BaseModel):
    """Delete request schema."""
    id: str | None = None  # Opcional, puede venir del token
