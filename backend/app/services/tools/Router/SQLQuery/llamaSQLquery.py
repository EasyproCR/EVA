from __future__ import annotations

from sqlalchemy import create_engine
from llama_index.core import SQLDatabase


class LlamaSQLQuery:
    """Builder mínimo: URI -> SQLAlchemy engine -> SQLDatabase (LlamaIndex)."""

    def __init__(self, connection_uri: str):
        self.connection_uri = connection_uri
        self.sqlalchemy_engine = create_engine( self.connection_uri,
        pool_pre_ping=True,          # evita conexiones muertas
        pool_recycle=1800,           # recicla cada 30 min
        pool_timeout=30,
        connect_args={
        "connect_timeout": 30,
        "read_timeout": 30,
        "write_timeout": 30,
    },)
        self.sql_database = SQLDatabase(self.sqlalchemy_engine)

    def get_sql_database(self) -> SQLDatabase:
        return self.sql_database
