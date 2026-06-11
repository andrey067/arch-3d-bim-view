"""Centralized configuration via Pydantic Settings.

Sprint 0 declares every key the platform will need across sprints,
even though many are not consumed yet. This avoids re-touching
configuration as features land.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, RedisDsn, field_validator
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

    # --- Database ---
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://app3d:app3d@localhost:5432/app3d",
        description="SQLAlchemy URL.",
    )
    DB_POOL_PRE_PING: bool = True
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # --- Redis ---
    REDIS_URL: RedisDsn = Field(
        default=RedisDsn("redis://localhost:6379/0"),
        description="Redis connection URL.",
    )

    # --- Celery ---
    CELERY_BROKER_URL: RedisDsn = Field(
        default=RedisDsn("redis://localhost:6379/1"),
    )
    CELERY_RESULT_BACKEND: RedisDsn = Field(
        default=RedisDsn("redis://localhost:6379/2"),
    )

    # --- Storage ---
    STORAGE_BACKEND: Literal["local"] = "local"
    STORAGE_ROOT: str = "./storage"

    # --- Security ---
    JWT_SECRET: str = Field(
        default="dev-only-change-me",
        description="HMAC secret for access tokens. Override in prod.",
    )
    JWT_ALG: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_TTL_S: int = 900  # 15 min
    REFRESH_TOKEN_TTL_D: int = 30
    PASSWORD_HASH_SCHEME: Literal["bcrypt", "argon2id"] = "bcrypt"

    # --- Limits ---
    MAX_UPLOAD_MB: int = 100
    MAX_CONVERSION_TIMEOUT_S: int = 600
    MAX_CONVERSION_ATTEMPTS: int = 3

    # --- Thumbnail ---
    THUMBNAIL_SIZE_W: int = 800
    THUMBNAIL_SIZE_H: int = 600

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
