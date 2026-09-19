"""Application settings, loaded from the environment (and `.env` locally)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GoldSeats API"
    api_v1_prefix: str = "/api/v1"

    goldseats_env: Environment = "local"
    log_level: str = "INFO"
    log_json: bool = False

    # SQLite by default so the API runs with no Docker and no external services.
    database_url: str = "sqlite+pysqlite:///./goldseats.db"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    tmdb_api_key: str | None = None
    redis_url: str | None = None

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.goldseats_env == "production"

    @property
    def uses_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
