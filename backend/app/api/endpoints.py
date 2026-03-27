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
    response_obj = orch.procesar_mensaje(
        mensaje_limpio or request.mensaje,
        session_id=user_info.get("id", ""),
        nombreUsuario=user_info.get("nombre", ""),
        user_roles=user_info.get("roles", []),
    )
    response_text = str(response_obj)
    return ChatResponse(respuesta=response_text, id=user_info.get("id", ""))

@router.get("/saludo")
async def saludo(
    http_req: Request,
    user_info: dict = Depends(get_user_info_dependency),
    nombre: str = None
) -> dict:
    """
    Endpoint de saludo inicial con recordatorios automáticos para RRHH.
    GET /api/saludo?nombre=Juan
    """
    # Intenta obtener nombre del query param, si no está, del token
    nombre_final = (nombre or "").strip()
    if not nombre_final:
        nombre_final = (user_info.get('nombre', '') or "").strip()

    # Saludo base
    if nombre_final:
        saludo_texto = f"¡Hola {nombre_final}! Soy EVA, tu asistente de IA."
    else:
        saludo_texto = "¡Hola! Soy EVA, tu asistente de IA."

    # Verificar recordatorios para usuarios de RRHH
    user_roles = user_info.get('roles', [])
    recordatorios_info = None

    try:
        orch = http_req.app.state.orch
        reminders_result = orch.get_rrhh_reminders(user_roles)

        if reminders_result.get("authorized") and reminders_result.get("count", 0) > 0:
            # Construir mensaje de recordatorios
            count = reminders_result["count"]
            reminders = reminders_result["reminders"]

            recordatorios_texto = f"\n\n📋 **Tienes {count} alerta(s) pendiente(s):**\n"
            for r in reminders:
                emoji = r.get('emoji', '🔵')
                titulo = r.get('titulo', 'Sin título')
                fecha = r.get('fecha_vencimiento', '')
                accion = r.get('accion', '')

                if fecha and fecha != 'None' and fecha != '':
                    recordatorios_texto += f"\n{emoji} **{titulo}** - Vence: {fecha}"
                else:
                    recordatorios_texto += f"\n{emoji} **{titulo}**"

                # Mostrar sugerencia de acción si existe
                if accion:
                    recordatorios_texto += f"\n   _→ {accion}_"

            saludo_texto += recordatorios_texto
            recordatorios_info = {
                "count": count,
                "reminders": reminders
            }
        elif reminders_result.get("authorized") and reminders_result.get("count", 0) == 0:
            saludo_texto += "\n\n✅ ¡Todo en orden! No tienes alertas pendientes."
            recordatorios_info = {"count": 0, "reminders": []}
    except Exception as e:
        # Si falla, solo mostrar saludo básico
        pass

    saludo_texto += "\n\n¿En qué puedo ayudarte hoy?"

    response = {"saludo": saludo_texto}
    if recordatorios_info is not None:
        response["recordatorios"] = recordatorios_info

    return response

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
