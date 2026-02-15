from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from urllib.parse import quote_plus


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


    easychat_secret: str = ""
    easychat_url: str = "http://localhost:5173"
    
    openai_api_key: str =""
    openai_model: str = "gpt-4.1"
    openai_max_tokens: int = 2000

    tavily_api_key: str | None = None

    # ===== EasyCore =====
    easycore_host: str = "easycoredb.mysql.database.azure.com"
    easycore_db: str = "easycoredb"
    easycore_username: str = "azuresuperuser"
    easycore_password: str = ""
    easycore_port: int = 3306

    # ===== Bienes =====
    bienes_host: str = ""
    bienes_db: str = ""
    bienes_username: str = ""
    bienes_password: str = ""
    bienes_port: int = 3306

    # App
    app_name: str = "EVA Backend"
    app_version: str = "1.0.0"
    debug: bool = False



    

    @computed_field
    @property
    def DB_URI_EASYCORE(self) -> str:
        user = quote_plus(self.easycore_username)
        pwd = quote_plus(self.easycore_password)
        return f"mysql+pymysql://{user}:{pwd}@{self.easycore_host}:{self.easycore_port}/{self.easycore_db}?"

    @computed_field
    @property
    def DB_URI_BIENES(self) -> str:
        if not self.bienes_host or not self.bienes_db or not self.bienes_username:
            raise ValueError(
                "Config incompleta para BIENES. Requiere BIENES_HOST, BIENES_DB, BIENES_USERNAME y BIENES_PASSWORD en .env"
            )
        user = quote_plus(self.bienes_username)
        pwd = quote_plus(self.bienes_password)
        return f"mysql+pymysql://{user}:{pwd}@{self.bienes_host}:{self.bienes_port}/{self.bienes_db}"



def get_settings() -> Settings:
    return Settings()
