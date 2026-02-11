"""
EasycoreAuth - Input validation for user requests
Adapted from JavaScript InputUser class
"""

import re
import jwt
from typing import Any
from app.core.config import get_settings


class EasycoreAuth:
    """User input validation and cleaning."""
    
    @staticmethod
    def _to_trimmed_string(value: Any) -> str:
        """Convert value to trimmed string."""
        if value is None:
            return ""
        return str(value).strip()
    
    @staticmethod
    def _clean_text(value: Any) -> str:
        """
        Normalize to a safe, readable string for OpenAI prompts.
        Remove ASCII control chars except common whitespace (tab/newline).
        Collapse excessive spaces (keep newlines).
        """
        text = EasycoreAuth._to_trimmed_string(value)
        # Remove ASCII control chars except common whitespace (tab/newline)
        without_controls = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        # Collapse excessive spaces (keep newlines)
        return re.sub(r'[ \t]{2,}', ' ', without_controls)
    
    @staticmethod
    def decode_token(token: str) -> dict:
        """
        Decodifica el JWT token y extrae id y nombre del usuario.
        Retorna dict con ok, error, y value (id, nombre).
        """
        if not token:
            return {"ok": False, "error": "Token no proporcionado"}
        
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        settings = get_settings()
        secret = settings.easychat_secret
        
        if not secret:
            return {"ok": False, "error": "EASYCHAT_SECRET no configurado"}
        
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            user_id = EasycoreAuth._to_trimmed_string(payload.get("id"))
            nombre = EasycoreAuth._clean_text(payload.get("nombre"))
            
            print(f"Token decodificado: id='{user_id}', nombre='{nombre}'")
            
            return {
                "ok": True,
                "value": {"id": user_id, "nombre": nombre}
            }
        except jwt.ExpiredSignatureError:
            return {"ok": False, "error": "Token expirado"}
        except jwt.InvalidTokenError as e:
            return {"ok": False, "error": f"Token inválido: {str(e)}"}
    
    @staticmethod
    def from_chat_body(body: Any) -> dict:
        """Validate chat request body."""
        if not body or not isinstance(body, dict):
            return {"ok": False, "error": "Body inválido (se esperaba JSON)"}
        
        id_val = EasycoreAuth._to_trimmed_string(body.get("id"))
        nombre = EasycoreAuth._clean_text(body.get("nombre"))
        mensaje = EasycoreAuth._clean_text(body.get("mensaje"))

        print (f"Validando body: id='{id_val}', nombre='{nombre}', mensaje='{mensaje}'")
        return {"ok": True, "value": {"id": id_val, "nombre": nombre, "mensaje": mensaje}}
    
    @staticmethod
    def from_delete_body(body: Any) -> dict:
        """Validate delete request body."""
        if not body or not isinstance(body, dict):
            return {"ok": False, "error": "Body inválido (se esperaba JSON)"}
        
        id_val = EasycoreAuth._to_trimmed_string(body.get("id"))
        print (f"Validando body para eliminar: id='{id_val}'")
        return {"ok": True, "value": {"id": id_val}}
