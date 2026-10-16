"""LangChain tools wrapping deterministic database lookups, scoring, and genuine resources."""

from typing import Any
from langchain_core.tools import tool

from app.services.agents.resource_registry import resource_registry


@tool
def tool_lookup_genuine_resources(skills: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Look up authoritative, verified learning resources for technical skills without hallucinating links."""
    return resource_registry.get_resources_for_skills(skills, limit_per_skill=2)


@tool
def tool_validate_resource_url(url: str) -> bool:
    """Validate that a URL uses HTTPS and belongs to an approved official documentation domain."""
    from app.services.agents.resource_registry import is_url_genuine
    return is_url_genuine(url)


# Export tool definitions for agent tool binding
AGENT_TOOLS = [
    tool_lookup_genuine_resources,
    tool_validate_resource_url,
]

# Aliases
lookup_official_learning_resources = tool_lookup_genuine_resources
verify_resource_url = tool_validate_resource_url

