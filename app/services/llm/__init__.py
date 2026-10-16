"""LLM services package exposing provider interfaces, factory, and Career Twin generators."""

from app.services.llm.base import (
    BaseLLMProvider,
    LLMInferenceError,
    LLMMessage,
    LLMResponse,
    StructuredOutputError,
    extract_json_from_text,
)
from app.services.llm.career_tasks import CareerTaskService, career_task_service
from app.services.llm.factory import LLMProviderFactory, get_llm_provider, llm_factory
from app.services.llm.local_transformers import LocalTransformersProvider
from app.services.llm.mock_provider import MockLLMProvider

__all__ = [
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
    "LLMInferenceError",
    "StructuredOutputError",
    "extract_json_from_text",
    "LocalTransformersProvider",
    "MockLLMProvider",
    "LLMProviderFactory",
    "get_llm_provider",
    "llm_factory",
    "CareerTaskService",
    "career_task_service",
]
