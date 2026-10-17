"""Provider factory and lifecycle manager for LLM services."""

import logging
import os
from app.core.config import settings
from app.services.llm.base import BaseLLMProvider
from app.services.llm.mock_provider import MockLLMProvider

logger = logging.getLogger("kuru.llm.factory")


class LLMProviderFactory:
    """Factory creating and caching LLM inference providers based on configuration."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseLLMProvider] = {}

    def get_provider(self, provider_name: str | None = None) -> BaseLLMProvider:
        """Get or initialize the requested LLM provider."""
        target = (provider_name or settings.LLM_PROVIDER).lower().strip()

        is_serverless = os.environ.get("VERCEL") == "1" or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
        if settings.ENVIRONMENT == "production" and not is_serverless:
            if target == "mock":
                raise ValueError(
                    "Mock LLM provider is strictly prohibited in production environment. "
                    "Configure a valid inference provider (e.g. LLM_PROVIDER='local')."
                )
            if target not in {"local", "openai_compatible"}:
                raise ValueError(
                    f"Invalid LLM provider '{target}' for production. "
                    "Must be 'local' or 'openai_compatible'."
                )

        if target not in self._providers:
            if target == "local":
                logger.info("Initializing LocalTransformersProvider for local model inference...")
                from app.services.llm.local_transformers import LocalTransformersProvider
                self._providers[target] = LocalTransformersProvider()
            elif target == "mock":
                logger.info("Initializing MockLLMProvider (test/development mode)...")
                self._providers[target] = MockLLMProvider()
            else:
                logger.warning(
                    "Unrecognized provider '%s'; defaulting to MockLLMProvider.", target
                )
                self._providers[target] = MockLLMProvider()

        return self._providers[target]

    def reset(self) -> None:
        """Clear cached providers (useful for test isolation)."""
        self._providers.clear()


llm_factory = LLMProviderFactory()


def get_llm_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """Convenience accessor for active LLM provider."""
    return llm_factory.get_provider(provider_name)
