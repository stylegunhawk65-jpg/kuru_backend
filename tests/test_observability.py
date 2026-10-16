"""Unit and integration tests for LangSmith observability and diagnostic services."""

from unittest.mock import MagicMock, patch
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services.observability.langsmith_service import (
    get_langsmith_diagnostic,
    mask_api_key,
    setup_langsmith_environment,
)


def test_mask_api_key():
    """Verify that sensitive API keys are never leaked in logs or diagnostics."""
    assert mask_api_key(None) is None
    assert mask_api_key("") is None
    assert mask_api_key("short") == "****"
    assert mask_api_key("12345678") == "****"

    masked = mask_api_key("lsv2_pt_abcdef1234567890xyz")
    assert masked is not None
    assert masked.startswith("lsv2_pt_")
    assert masked.endswith("0xyz")
    assert "abcdef" not in masked
    assert "..." in masked


def test_diagnostic_disabled():
    """When tracing is disabled, diagnostic correctly returns disabled status."""
    with patch.object(settings, "LANGSMITH_TRACING", False):
        diag = get_langsmith_diagnostic(verify_connectivity=False)
        assert diag.enabled is False
        assert diag.status == "disabled"
        assert "disabled" in diag.guidance.lower()


def test_diagnostic_unconfigured():
    """When tracing is requested without an API key, status is unconfigured without faking."""
    with patch.object(settings, "LANGSMITH_TRACING", True), patch.object(
        settings, "LANGSMITH_API_KEY", None
    ), patch.dict("os.environ", {}, clear=True):
        diag = get_langsmith_diagnostic(verify_connectivity=False)
        assert diag.enabled is True
        assert diag.configured is False
        assert diag.status == "unconfigured"
        assert "LANGSMITH_API_KEY" in diag.guidance
        assert "https://smith.langchain.com" in diag.guidance


def test_diagnostic_configured_offline():
    """When API key is present without online check, returns configured with masked key."""
    test_key = "lsv2_pt_testkey1234567890test"
    with patch.object(settings, "LANGSMITH_TRACING", True), patch.object(
        settings, "LANGSMITH_API_KEY", test_key
    ):
        diag = get_langsmith_diagnostic(verify_connectivity=False)
        assert diag.enabled is True
        assert diag.configured is True
        assert diag.status == "configured"
        assert diag.project == "kuru-career-twin"
        assert diag.masked_api_key == mask_api_key(test_key)


def test_diagnostic_invalid_key_online():
    """When online verification encounters 403 Forbidden, reports invalid_key."""
    from langsmith.utils import LangSmithError

    test_key = "lsv2_pt_invalidkey1234567890"
    with patch.object(settings, "LANGSMITH_TRACING", True), patch.object(
        settings, "LANGSMITH_API_KEY", test_key
    ), patch("langsmith.Client.list_projects", side_effect=LangSmithError("403 Forbidden")):
        diag = get_langsmith_diagnostic(verify_connectivity=True)
        assert diag.enabled is True
        assert diag.status == "invalid_key"
        assert "rejected" in diag.guidance.lower()


def test_setup_langsmith_environment():
    """setup_langsmith_environment exports variables only when key is provided."""
    test_key = "lsv2_pt_envtest1234567890"
    with patch.object(settings, "LANGSMITH_TRACING", True), patch.object(
        settings, "LANGSMITH_API_KEY", test_key
    ):
        diag = setup_langsmith_environment()
        assert diag.enabled is True
        import os
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        assert os.environ.get("LANGCHAIN_API_KEY") == test_key
        assert os.environ.get("LANGCHAIN_PROJECT") == "kuru-career-twin"

    # When unconfigured, ensure tracing is not set to true
    with patch.object(settings, "LANGSMITH_TRACING", True), patch.object(
        settings, "LANGSMITH_API_KEY", None
    ), patch.dict("os.environ", {}, clear=True):
        diag = setup_langsmith_environment()
        import os
        assert os.environ.get("LANGCHAIN_TRACING_V2") != "true"


@pytest.mark.asyncio
async def test_observability_health_endpoint(async_client: AsyncClient):
    """GET /api/v1/health/observability returns diagnostic response schema."""
    response = await async_client.get("/api/v1/health/observability")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "project" in data
    assert data["project"] == "kuru-career-twin"
    assert "status" in data
    assert "endpoint" in data
