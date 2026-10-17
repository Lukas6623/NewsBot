from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    telegram_bot_token: str = ""
    telegram_admin_ids: str = ""
    database_path: Path = Path("./data/serverguard.sqlite3")
    media_path: Path = Path("./data/media")
    public_site_url: str = "https://serverguard.site"
    public_api_url: str = ""
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "https://serverguard.site,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8080,http://127.0.0.1:8080"
    ping_timeout_seconds: float = 10.0
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_ids(self) -> frozenset[int]:
        return frozenset(int(value.strip()) for value in self.telegram_admin_ids.split(",") if value.strip().isdigit())

    @property
    def origins(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
