"""
IAServicio - Superclase base para endpoints de IA
Contiene lógica común de validación y utilidades
"""

from fastapi import HTTPException, Header, Depends, Request
from app.services.easycore_auth import EasycoreAuth



# Dependencia para extraer y decodificar el usuario desde el header Authorization
async def get_user_info_dependency(authorization: str = Header(None)) -> dict:
    """
    Decodifica el JWT y retorna info de usuario y autenticación.
    """
    if not authorization:
        return {"authenticated": False}
    result = EasycoreAuth.decode_token(authorization)
    if result["ok"]:
        return {
            "id": result["value"]["id"],
            "nombre": result["value"]["nombre"],
            "authenticated": True
        }
    return {"authenticated": False}

# Dependencia para requerir autenticación
async def require_auth_dependency(user_info: dict = Depends(get_user_info_dependency)):
    if not user_info.get("authenticated"):
        raise HTTPException(status_code=401, detail="No autenticado")

# Dependencia para limpiar el mensaje
async def validate_mensaje_dependency(request: Request) -> str:
    body = await request.json()
    mensaje = body.get("mensaje", "")
    return EasycoreAuth._clean_text(mensaje)

# Dependencia para validar el body de eliminación
async def validate_delete_body_dependency(request: Request) -> dict:
    body = await request.json()
    validation = EasycoreAuth.from_delete_body(body)
    if not validation["ok"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    return validation["value"]
