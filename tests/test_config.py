"""Tests for configuration parsing, validation, and security constraints."""

import pytest
from pydantic import ValidationError
from app.core.config import Settings, parse_cors_origins
from app.core.logging import SensitiveDataFilter


def test_cors_origins_parsing():
    """Test string and list parsing for CORS origins."""
    assert parse_cors_origins("http://a.com, http://b.com/") == ["http://a.com", "http://b.com"]
    assert parse_cors_origins(["http://a.com/", "http://b.com"]) == ["http://a.com", "http://b.com"]
    assert parse_cors_origins("") == []
    assert parse_cors_origins(None) == []


def test_cors_wildcard_rejected_in_production():
    """Ensure wildcard CORS is prohibited when ENVIRONMENT=production."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["*"],
            _env_file=None,
        )
    assert "Wildcard '*' CORS origin is not permitted in production" in str(exc_info.value)


def test_database_url_conversion():
    """Ensure standard postgresql:// URL is automatically upgraded to postgresql+asyncpg://."""
    s = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        _env_file=None,
    )
    assert s.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"

    s2 = Settings(
        DATABASE_URL="postgres://user:pass@localhost:5432/db",
        _env_file=None,
    )
    assert s2.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"


def test_sensitive_data_filter_masks_credentials():
    """Test sensitive data filter scrubs secrets from strings."""
    filter_instance = SensitiveDataFilter()

    # Password masking
    msg1 = "User attempted login with password: MySecretPassword123!"
    masked1 = filter_instance.mask_sensitive(msg1)
    assert "MySecretPassword123!" not in masked1
    assert "[REDACTED]" in masked1

    # Bearer token masking
    msg2 = "Authorization Header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    masked2 = filter_instance.mask_sensitive(msg2)
    assert "Bearer [REDACTED]" in masked2

    # Database connection URL password masking
    msg3 = "Connecting to postgresql+asyncpg://myuser:supersecretpass@db.example.com:5432/kuru"
    masked3 = filter_instance.mask_sensitive(msg3)
    assert "supersecretpass" not in masked3
    assert "****" in masked3
