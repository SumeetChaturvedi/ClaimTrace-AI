from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg2://claimtrace:claimtrace@localhost:5432/claimtrace"
    )
    storage_root: Path = Path("./storage")
    app_env: str = "development"

    default_project_name: str = "Delhi Metro Viaduct Package DMV-7 (fictional)"


@lru_cache
def get_settings() -> Settings:
    return Settings()
