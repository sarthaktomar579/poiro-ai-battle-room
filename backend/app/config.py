"""Runtime configuration loaded from environment variables.

A single ``Settings`` instance is shared across the app. Values are read from
the OS environment and (optionally) from a ``.env`` file in the backend root.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core
    app_env: str = "development"
    secret_key: str = "dev-insecure-secret-change-me"
    access_token_expire_minutes: int = 60 * 24 * 7

    # Database
    database_url: str = "sqlite:///./data/poiro.db"

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # AI provider
    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Worker
    worker_concurrency: int = 3
    job_timeout_seconds: int = 45
    job_max_attempts: int = 2

    @field_validator("ai_provider")
    @classmethod
    def _normalize_provider(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in {"gemini", "mock"}:
            return "mock"
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
