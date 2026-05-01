"""
Stokvel OS — Centralised Configuration
========================================
All settings loaded from environment variables via pydantic-settings.
The app will refuse to start if required vars are missing.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings — loaded from .env / environment."""

    # ── Required ──
    jwt_secret: str = Field(..., min_length=16, description="JWT signing secret")
    database_url: str = Field(..., description="PostgreSQL async connection string")
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── AWS SES ──
    aws_region: str = Field(default="af-south-1")
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    ses_sender_email: str = Field(default="noreply@stokvel.co.za")

    # ── App ──
    environment: str = Field(default="development")
    port: int = Field(default=8000)
    otp_expiry_seconds: int = Field(default=300)
    otp_length: int = Field(default=6)

    # ── JWT ──
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_not_placeholder(cls, v: str) -> str:
        if v in ("changeme", "secret", ""):
            raise ValueError("JWT_SECRET must be set to a real secret, not a placeholder")
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    """Singleton settings — cached after first call."""
    return Settings()
