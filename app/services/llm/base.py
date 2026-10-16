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


def attempt_json_repair(text: str) -> str | None:
    """Attempt basic repairs for truncated or trailing delimiter JSON strings."""
    text = text.strip()
    if not text:
        return None

    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    in_string = False
    escape = False
    stack = []
    for char in text:
        if char == '\\' and not escape:
            escape = True
            continue
        if char == '"' and not escape:
            in_string = not in_string
        elif not in_string:
            if char == '{':
                stack.append('}')
            elif char == '[':
                stack.append(']')
            elif char in ('}', ']'):
                if stack and stack[-1] == char:
                    stack.pop()
        escape = False

    repaired = text
    if in_string:
        repaired += '"'
    while stack:
        repaired += stack.pop()

    try:
        json.loads(repaired)
        return repaired
    except Exception:
        repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
        try:
            json.loads(repaired)
            return repaired
        except Exception:
            return None


def generate_schema_skeleton(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Build an exemplar JSON skeleton for LLMs to guide clean instance generation."""
    from typing import get_args, get_origin, Union

    res: dict[str, Any] = {}
    for name, field in model_cls.model_fields.items():
        ann = field.annotation
        origin = get_origin(ann)
        args = get_args(ann)

        if origin is Union:
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                ann = non_none[0]
                origin = get_origin(ann)
                args = get_args(ann)

        if origin is list:
            sub = args[0] if args else str
            if isinstance(sub, type) and issubclass(sub, BaseModel):
                res[name] = [generate_schema_skeleton(sub)]
            elif sub is int:
                res[name] = [1]
            elif sub is float:
                res[name] = [0.0]
            else:
                desc = field.description or "string"
                res[name] = [desc]
        elif isinstance(ann, type) and issubclass(ann, BaseModel):
            res[name] = generate_schema_skeleton(ann)
        elif ann is str:
            res[name] = field.description or "string"
        elif ann is int:
            res[name] = 1
        elif ann is float:
            res[name] = 0.0
        elif ann is bool:
            res[name] = True
        else:
            res[name] = "string"
    return res


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
        skeleton_dict = generate_schema_skeleton(schema)
        skeleton_json = json.dumps(skeleton_dict, indent=2)
        guidance = (
            f"You MUST output valid JSON strictly matching this structure and field names:\n"
            f"```json\n{skeleton_json}\n```\n"
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
            repaired = attempt_json_repair(extracted_json)
            if repaired:
                try:
                    return schema.model_validate_json(repaired)
                except Exception:
                    pass
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
