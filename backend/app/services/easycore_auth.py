"""
EasycoreAuth - Input validation for user requests
Adapted from JavaScript InputUser class
"""

import logging
import re
import jwt
from typing import Any
from app.core.config import get_settings
from app.services.llamaOrchestor import LlamaOrchestor


logger = logging.getLogger(__name__)


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
        normalized_token = EasycoreAuth._normalize_authorization_header(token)

        if not normalized_token:
            return {"ok": False, "error": "Token no proporcionado"}

        settings = get_settings()
        secret = settings.easychat_secret

        if not secret:
            return {"ok": False, "error": "EASYCHAT_SECRET no configurado"}

        try:
            payload = jwt.decode(
                normalized_token,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )

            user_id = EasycoreAuth._extract_user_id(payload)
            nombre = EasycoreAuth._extract_user_name(payload)

            if not user_id:
                return {"ok": False, "error": "Token válido pero sin identificador de usuario"}

            roles = EasycoreAuth._extract_roles(payload)

            logger.info("Token decodificado: id='%s', nombre='%s'", user_id, nombre)

            return {
                "ok": True,
                "value": {"id": user_id, "nombre": nombre, "roles": roles}
            }
        except jwt.ExpiredSignatureError:
            return {"ok": False, "error": "Token expirado"}
        except jwt.InvalidTokenError as e:
            return {"ok": False, "error": f"Token inválido: {str(e)}"}

    @staticmethod
    def _normalize_authorization_header(value: Any) -> str:
        """Accept common Authorization formats and return raw JWT token."""
        token = EasycoreAuth._to_trimmed_string(value).strip("\"'")
        if not token:
            return ""

        # Handle case-insensitive Bearer prefix and extra spaces.
        if token.lower().startswith("bearer"):
            parts = token.split(None, 1)
            if len(parts) == 2:
                token = parts[1].strip().strip("\"'")

        return token

    @staticmethod
    def _extract_user_id(payload: dict) -> str:
        """Extract user id from common JWT claim names."""
        candidates = [
            payload.get("id"),
            payload.get("user_id"),
            payload.get("uid"),
            payload.get("sub"),
        ]

        nested_user = payload.get("user")
        if isinstance(nested_user, dict):
            candidates.extend(
                [
                    nested_user.get("id"),
                    nested_user.get("user_id"),
                    nested_user.get("uid"),
                    nested_user.get("sub"),
                ]
            )

        for value in candidates:
            normalized = EasycoreAuth._to_trimmed_string(value)
            if normalized:
                return normalized

        return ""

    @staticmethod
    def _extract_user_name(payload: dict) -> str:
        """Extract user display name from common JWT claim names."""
        candidates = [
            payload.get("nombre"),
            payload.get("name"),
            payload.get("username"),
            payload.get("preferred_username"),
            payload.get("given_name"),
        ]

        nested_user = payload.get("user")
        if isinstance(nested_user, dict):
            candidates.extend(
                [
                    nested_user.get("nombre"),
                    nested_user.get("name"),
                    nested_user.get("username"),
                ]
            )

        for value in candidates:
            normalized = EasycoreAuth._clean_text(value)
            if normalized:
                return normalized

        return ""

    @staticmethod
    def _extract_roles(payload: dict) -> list[str]:
        raw_roles = payload.get("roles")

        if isinstance(raw_roles, list):
            return [EasycoreAuth._clean_text(v) for v in raw_roles if EasycoreAuth._to_trimmed_string(v)]

        if isinstance(raw_roles, str):
            return [EasycoreAuth._clean_text(raw_roles)] if EasycoreAuth._to_trimmed_string(raw_roles) else []

        single_role = payload.get("role")
        if EasycoreAuth._to_trimmed_string(single_role):
            return [EasycoreAuth._clean_text(single_role)]

        return []
    
    @staticmethod
    def from_chat_body(body: Any) -> dict:
        """Validate chat request body."""
        if not body or not isinstance(body, dict):
            return {"ok": False, "error": "Body inválido (se esperaba JSON)"}
        
        id_val = EasycoreAuth._to_trimmed_string(body.get("id"))
        nombre = EasycoreAuth._clean_text(body.get("nombre"))
        mensaje = EasycoreAuth._clean_text(body.get("mensaje"))

        logger.debug("Validando body: id='%s', nombre='%s'", id_val, nombre)
        return {"ok": True, "value": {"id": id_val, "nombre": nombre, "mensaje": mensaje}}
    
    @staticmethod
    def from_delete_body(body: Any) -> dict:
        """Validate delete request body."""
        if not body or not isinstance(body, dict):
            return {"ok": False, "error": "Body inválido (se esperaba JSON)"}
        
        id_val = EasycoreAuth._to_trimmed_string(body.get("id"))
        logger.debug("Validando body para eliminar: id='%s'", id_val)
        return {"ok": True, "value": {"id": id_val}}
