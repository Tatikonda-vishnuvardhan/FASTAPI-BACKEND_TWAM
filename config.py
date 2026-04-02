"""
config.py
──────────
Centralised configuration using pydantic-settings.
All environment variables are validated at startup — missing required
vars raise a clear RuntimeError instead of failing silently later.

Usage:
    from config import settings
    print(settings.database_url)
"""

from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str

    # ── JWT ───────────────────────────────────────────────────────────────────
    secret_key:          str
    jwt_algorithm:       str = "HS512"
    jwt_issuer:          str = "http://127.0.0.1:8000"
    jwt_audience:        str = "twam-web-portal"
    jwt_expires_minutes: int = 60

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated origins.
    # Example: "https://app.twam.in,https://admin.twam.in,capacitor://localhost"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,capacitor://localhost,http://localhost"

    # ── File Storage ─────────────────────────────────────────────────────────
    base_url: str = ""

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_exist(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be set in .env and be at least 32 characters. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    @field_validator("database_url")
    @classmethod
    def database_url_must_exist(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must be set in .env")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


# ── Singleton instance ────────────────────────────────────────────────────────
settings = Settings()
