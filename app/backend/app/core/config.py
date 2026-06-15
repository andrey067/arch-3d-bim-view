"""Centralized configuration via Pydantic Settings.

Simplified MVP: SQLite, local disk storage, no auth/Celery/Redis.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Runtime ---
    APP_ENV: Literal["dev", "test", "prod"] = "dev"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # --- Database (SQLite) ---
    DATABASE_URL: str = Field(
        default="sqlite:///./app.db",
        description="SQLAlchemy URL. Default is SQLite.",
    )

    # --- Storage ---
    STORAGE_ROOT: str = "../../storage"

    # --- Conversion tool paths ---
    IFCCONVERT_PATH: str = "IfcConvert"
    USD_FROM_GLTF_PATH: str = "usd_from_gltf"
    MAX_CONVERSION_ATTEMPTS: int = 3

    # --- Limits ---
    MAX_UPLOAD_MB: int = 100

    # --- CORS ---
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    # --- Public base URL (for share links / AR) ---
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def is_production(self) -> bool:
        return self.APP_ENV == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
