# app/core/config.py
"""
Configuration management for the multi-tenant application.

Reason: Centralized configuration with environment variable support,
type validation, and clear separation of concerns.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, validator
from typing import Optional
import secrets


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application Configuration
    APP_NAME: str = Field(default="MultiTenant FastAPI", env="APP_NAME")
    DEBUG: bool = Field(default=False, env="DEBUG")
    VERSION: str = Field(default="1.0.0", env="VERSION")

    # Database Configuration
    TENANT_DATABASE_URL: PostgresDsn = Field(
        default="postgresql://postgres:password@localhost:5432/tenant_db",
        env="TENANT_DATABASE_URL"
    )

    # Security Configuration
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        env="SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Tenant Configuration
    TENANT_HEADER: str = Field(default="X-Tenant-ID", env="TENANT_HEADER")
    DEFAULT_ADMIN_EMAIL: str = Field(default="admin@system.com", env="DEFAULT_ADMIN_EMAIL")
    DEFAULT_ADMIN_PASSWORD: str = Field(default="admin123", env="DEFAULT_ADMIN_PASSWORD")

    # Migration Configuration
    MIGRATION_BATCH_SIZE: int = Field(default=10, env="MIGRATION_BATCH_SIZE")
    MIGRATION_TIMEOUT: int = Field(default=300, env="MIGRATION_TIMEOUT")

    # Database Pool Configuration
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=10, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=3600, env="DB_POOL_RECYCLE")

    @validator("TENANT_DATABASE_URL", pre=True)
    def validate_db_url(cls, v: str) -> str:
        """Validate database URL format."""
        if isinstance(v, str):
            if "postgresql://" not in v and "postgres://" not in v:
                raise ValueError("Database URL must start with postgresql://")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create global settings instance
settings = Settings()