from __future__ import annotations

import logging
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _easycore_engine():
    settings = get_settings()

    return create_engine(
        settings.DB_URI_EASYCORE,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
        connect_args={
            "connect_timeout": 30,
            "read_timeout": 30,
            "write_timeout": 30,
        },
    )


class EasycoreUserRolesService:
    @staticmethod
    def get_roles_for_user(user_id: str) -> list[str]:
        normalized_id = str(user_id or "").strip()

        if not normalized_id.isdigit():
            return []

        sql = text(
            """
            SELECT DISTINCT r.name
            FROM model_has_roles mhr
            INNER JOIN roles r ON r.id = mhr.role_id
            WHERE mhr.model_id = :user_id
              AND mhr.model_type LIKE :model_type
            """
        )

        try:
            with _easycore_engine().connect() as conn:
                rows = conn.execute(
                    sql,
                    {
                        "user_id": int(normalized_id),
                        "model_type": "%User",
                    },
                ).fetchall()

            return [str(row[0]).strip() for row in rows if row and row[0]]
        except SQLAlchemyError as exc:
            logger.warning("No se pudieron obtener roles de EasyCore para user_id=%s: %s", normalized_id, exc)
            return []
