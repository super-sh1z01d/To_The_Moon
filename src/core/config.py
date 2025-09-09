from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Basics
    app_name: str = Field(default="to-the-moon")
    app_version: str = Field(default="0.1.0-iter0")
    app_env: str = Field(default="dev")  # dev/stage/prod
    log_level: str = Field(default="INFO")

    # HTTP server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # Database
    database_url: Optional[str] = None

    # Frontend
    frontend_dist_path: Optional[str] = Field(default="frontend/dist")

    # Scheduler
    scheduler_enabled: bool = Field(default=True)


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()  # type: ignore[call-arg]
