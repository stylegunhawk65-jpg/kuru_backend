"""LangSmith tracing configuration, safe startup diagnostics, and trace management."""

from datetime import datetime, timezone
import logging
import os
from typing import Any
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("kuru.observability.langsmith")


def mask_api_key(api_key: str | None) -> str | None:
    """Safely mask an API key for logs and diagnostics, exposing only prefix and suffix."""
    if not api_key:
        return None
    key_str = str(api_key).strip()
    if len(key_str) <= 10:
        return "****"
    if key_str.startswith("lsv2_pt_") or key_str.startswith("lsv2_sk_"):
        prefix = key_str[:8]
        suffix = key_str[-4:]
        return f"{prefix}...{suffix}"
    return f"{key_str[:4]}...{key_str[-4:]}"


class LangSmithDiagnostic(BaseModel):
    """Schema representing the observability status of LangSmith."""

    enabled: bool
    configured: bool
    project: str
    endpoint: str
    status: str  # connected, unconfigured, invalid_key, disabled, connection_error
    masked_api_key: str | None = None
    guidance: str | None = None
    verified_online: bool = False
    timestamp: str


def get_langsmith_guidance_message(status: str) -> str:
    """Return explicit instructions on how to configure LangSmith."""
    if status == "unconfigured":
        return (
            "LangSmith tracing is enabled, but no LANGSMITH_API_KEY (or LANGCHAIN_API_KEY) was found. "
            "To enable tracing for Kuru multi-agent workflows:\n"
            "  1. Sign in to https://smith.langchain.com/\n"
            "  2. Create an API key under Settings > API Keys\n"
            "  3. Set in your .env file or environment:\n"
            "       LANGSMITH_TRACING=true\n"
            "       LANGSMITH_API_KEY=lsv2_pt_your_actual_key\n"
            "       LANGSMITH_PROJECT=kuru-career-twin\n"
            "  4. Restart the backend service. Traces for all 9 agents, Qwen calls, "
            "failures, and approval pauses will automatically stream to LangSmith."
        )
    elif status == "invalid_key":
        return (
            "The configured LangSmith API key was rejected by the LangSmith API (401/403). "
            "Please check that your API key is valid and has not expired or been revoked at "
            "https://smith.langchain.com/settings."
        )
    elif status == "disabled":
        return (
            "LangSmith tracing is currently disabled. To enable, set LANGSMITH_TRACING=true "
            "and supply LANGSMITH_API_KEY in your .env file."
        )
    return "LangSmith is operating normally."


def get_langsmith_diagnostic(verify_connectivity: bool = False) -> LangSmithDiagnostic:
    """Evaluate LangSmith configuration status, credentials validity, and diagnostic guidance.

    Never fakes successful tracing if the key is missing or invalid.
    """
    now = datetime.now(timezone.utc).isoformat()
    enabled = bool(settings.LANGSMITH_TRACING)
    api_key = settings.LANGSMITH_API_KEY or os.environ.get("LANGCHAIN_API_KEY")
    project = settings.LANGSMITH_PROJECT or "kuru-career-twin"
    endpoint = settings.LANGSMITH_ENDPOINT or "https://api.smith.langchain.com"
    masked_key = mask_api_key(api_key)

    if not enabled:
        return LangSmithDiagnostic(
            enabled=False,
            configured=bool(api_key),
            project=project,
            endpoint=endpoint,
            status="disabled",
            masked_api_key=masked_key,
            guidance=get_langsmith_guidance_message("disabled"),
            verified_online=False,
            timestamp=now,
        )

    if not api_key:
        return LangSmithDiagnostic(
            enabled=True,
            configured=False,
            project=project,
            endpoint=endpoint,
            status="unconfigured",
            masked_api_key=None,
            guidance=get_langsmith_guidance_message("unconfigured"),
            verified_online=False,
            timestamp=now,
        )

    # Key is provided. If verification is requested, attempt validation with LangSmith Client
    verified_online = False
    current_status = "configured"

    if verify_connectivity:
        try:
            from langsmith import Client
            from langsmith.utils import LangSmithError

            client = Client(api_key=api_key, api_url=endpoint)
            # Try reading project or listing projects with limit=1 to test credentials
            try:
                _ = list(client.list_projects(limit=1))
                verified_online = True
                current_status = "connected"
            except LangSmithError as ls_err:
                err_str = str(ls_err).lower()
                if "401" in err_str or "403" in err_str or "forbidden" in err_str or "unauthorized" in err_str:
                    current_status = "invalid_key"
                else:
                    current_status = "connection_error"
            except Exception as exc:
                err_str = str(exc).lower()
                if "401" in err_str or "403" in err_str:
                    current_status = "invalid_key"
                else:
                    current_status = "connection_error"
        except ImportError:
            current_status = "missing_dependency"
    else:
        current_status = "configured"

    return LangSmithDiagnostic(
        enabled=True,
        configured=True,
        project=project,
        endpoint=endpoint,
        status=current_status,
        masked_api_key=masked_key,
        guidance=get_langsmith_guidance_message(current_status),
        verified_online=verified_online,
        timestamp=now,
    )


def setup_langsmith_environment() -> LangSmithDiagnostic:
    """Initialize LangSmith process environment variables at application startup.

    If tracing is enabled and credentials are provided, safely exports LANGCHAIN_*
    variables so LangGraph multi-agent pipelines and Qwen inference calls stream
    traces into the configured project.
    """
    diagnostic = get_langsmith_diagnostic(verify_connectivity=False)

    if diagnostic.enabled and diagnostic.configured and settings.LANGSMITH_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = diagnostic.project
        os.environ["LANGCHAIN_ENDPOINT"] = diagnostic.endpoint
        logger.info(
            "LangSmith tracing enabled for project '%s' (endpoint: %s, key: %s)",
            diagnostic.project,
            diagnostic.endpoint,
            diagnostic.masked_api_key,
        )
    elif diagnostic.enabled and not diagnostic.configured:
        # Avoid crashing or fake tracing; inform operator cleanly
        if "LANGCHAIN_TRACING_V2" in os.environ:
            os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.warning(
            "LangSmith tracing is requested (LANGSMITH_TRACING=true) but no API key was provided. "
            "Tracing remains unconfigured. Set LANGSMITH_API_KEY to activate."
        )
    else:
        logger.debug("LangSmith tracing is disabled (LANGSMITH_TRACING=false).")

    return diagnostic
