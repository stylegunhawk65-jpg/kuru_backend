"""Provider factory and lifecycle manager for LLM services."""

import logging
from app.core.config import settings
from app.services.llm.base import BaseLLMProvider
from app.services.llm.local_transformers import LocalTransformersProvider
from app.services.llm.mock_provider import MockLLMProvider

logger = logging.getLogger("kuru.llm.factory")


class LLMProviderFactory:
    """Factory creating and caching LLM inference providers based on configuration."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseLLMProvider] = {}

    def get_provider(self, provider_name: str | None = None) -> BaseLLMProvider:
        """Get or initialize the requested LLM provider."""
        target = (provider_name or settings.LLM_PROVIDER).lower().strip()

        if target not in self._providers:
            if target == "local":
                logger.info("Initializing LocalTransformersProvider for local model inference...")
                self._providers[target] = LocalTransformersProvider()
            elif target == "mock":
                logger.info("Initializing MockLLMProvider (fast deterministic testing)...")
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


def get_llm_provider() -> BaseLLMProvider:
    """Convenience accessor for active LLM provider."""
    return llm_factory.get_provider()
