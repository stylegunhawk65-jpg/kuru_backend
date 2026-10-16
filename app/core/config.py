"""Application settings and environment validation."""

from functools import lru_cache
from typing import Annotated, Any
from pydantic import BeforeValidator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors_origins(v: Any) -> list[str]:
    """Parse CORS origins from a comma-separated string or list."""
    if isinstance(v, str):
        if not v.strip():
            return []
        return [origin.strip().rstrip("/") for origin in v.split(",") if origin.strip()]
    elif isinstance(v, (list, tuple)):
        return [str(origin).strip().rstrip("/") for origin in v if str(origin).strip()]
    return []


class Settings(BaseSettings):
    """Application settings schema backed by environment variables."""

    # Project metadata
    PROJECT_NAME: str = "Kuru Backend"
    ENVIRONMENT: str = "development"  # development, testing, production
    DEBUG: bool = False
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS settings
    CORS_ORIGINS: Annotated[list[str], BeforeValidator(parse_cors_origins)] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    # Database configuration
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/kuru_db"
    )
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: float = 30.0

    # Logging
    LOG_LEVEL: str = "INFO"

    # Firebase Authentication
    FIREBASE_CREDENTIALS_PATH: str | None = None
    FIREBASE_PROJECT_ID: str | None = None

    # Security & Encryption for External Tokens
    ENCRYPTION_KEY: str = "kuru_dev_secret_key_32_bytes_safe_fallback_123="

    # GitHub Integration
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None

    # Job & Internship Data Sources (Optional credentials for partner APIs)
    ADZUNA_APP_ID: str | None = None
    ADZUNA_APP_KEY: str | None = None
    UNSTOP_API_KEY: str | None = None
    NAUKRI_API_KEY: str | None = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any) -> str:
        """Ensure postgresql connection uses the asyncpg driver."""
        if isinstance(v, str):
            # Convert standard sync postgresql:// url to postgresql+asyncpg://
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return str(v)

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: list[str], info: Any) -> list[str]:
        """Validate CORS origins for security in production."""
        # Check environment if accessible from values
        env = "development"
        if hasattr(info, "data") and "ENVIRONMENT" in info.data:
            env = info.data["ENVIRONMENT"]

        if env == "production":
            for origin in v:
                if origin == "*":
                    raise ValueError(
                        "Wildcard '*' CORS origin is not permitted in production environment."
                    )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings provider."""
    return Settings()


settings = get_settings()
