"""Base abstractions and data models for LLM inference providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import logging
import re
from typing import Any, TypeVar
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("kuru.llm")

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMMessage:
    """Chat message payload."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Standardized response from LLM generation."""

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_seconds: float = 0.0
    model_name: str = ""


class LLMInferenceError(Exception):
    """Raised when LLM inference fails due to timeout, OOM, or model errors."""

    def __init__(self, message: str, provider: str = "llm", cause: Exception | None = None):
        super().__init__(message)
        self.provider = provider
        self.cause = cause


class StructuredOutputError(LLMInferenceError):
    """Raised when generated output cannot be parsed into the expected Pydantic schema."""

    def __init__(self, message: str, raw_output: str, cause: Exception | None = None):
        super().__init__(message)
        self.raw_output = raw_output
        self.cause = cause


def extract_json_from_text(text: str) -> str:
    """Robustly extract JSON substring from Markdown fenced code blocks or raw text."""
    text = text.strip()
    # 1. Match ```json ... ``` code blocks
    fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1).strip()

    # 2. Match outermost { ... } or [ ... ] based on whichever delimiter appears first
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    has_brace = first_brace != -1 and last_brace != -1 and last_brace > first_brace

    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    has_bracket = first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket

    if has_brace and has_bracket:
        if first_brace < first_bracket:
            return text[first_brace : last_brace + 1].strip()
        return text[first_bracket : last_bracket + 1].strip()
    elif has_brace:
        return text[first_brace : last_brace + 1].strip()
    elif has_bracket:
        return text[first_bracket : last_bracket + 1].strip()

    return text


class BaseLLMProvider(ABC):
    """Abstract interface for local and remote LLM providers."""

    name: str

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if provider model weights are loaded and ready for inference."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate free-form text from prompt."""
        pass

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> T:
        """Generate structured JSON adhering to a Pydantic schema."""
        json_schema_str = json.dumps(schema.model_json_schema(), indent=2)
        guidance = (
            f"You MUST output valid JSON strictly matching this schema:\n"
            f"```json\n{json_schema_str}\n```\n"
            f"Do not include any prose before or after the JSON. Output only the JSON object."
        )

        full_system = f"{system_prompt}\n\n{guidance}" if system_prompt else guidance
        response = await self.generate(
            prompt=prompt,
            system_prompt=full_system,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        raw_text = response.text
        extracted_json = extract_json_from_text(raw_text)

        try:
            return schema.model_validate_json(extracted_json)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning(
                "Structured output parsing failed for schema '%s': %s. Raw text: %s",
                schema.__name__,
                exc,
                raw_text[:300],
            )
            # Try a single schema repair retry if malformed
            raise StructuredOutputError(
                f"Failed to parse LLM response into schema '{schema.__name__}': {exc}",
                raw_output=raw_text,
                cause=exc,
            )
