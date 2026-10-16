"""Centralized structured logging with sensitive data masking."""

import logging
import re
import sys
from typing import Any

# Patterns to mask sensitive data in log strings
SENSITIVE_PATTERNS = [
    (re.compile(r'(password|passwd|secret|token|api[_-]?key|authorization|bearer|langsmith[_-]?api[_-]?key|langchain[_-]?api[_-]?key)\s*[:=]\s*["\']?([^"\'\s,;]+)', re.IGNORECASE), r'\1: [REDACTED]'),
    (re.compile(r'Bearer\s+[a-zA-Z0-9_\-\.]+', re.IGNORECASE), r'Bearer [REDACTED]'),
    (re.compile(r'lsv2_[a-zA-Z0-9_]+', re.IGNORECASE), r'lsv2_***[REDACTED]***'),
    (re.compile(r'(postgres(?:ql)?(?:\+\w+)?://[^:]+:)([^@]+)(@)', re.IGNORECASE), r'\1****\3'),
]


class SensitiveDataFilter(logging.Filter):
    """Logging filter that scrubs passwords, tokens, credentials, and connection strings."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_sensitive(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._mask_value(k, v) for k, v in record.args.items()}
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    self.mask_sensitive(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True

    @staticmethod
    def mask_sensitive(text: str) -> str:
        """Apply masking patterns to a string."""
        for pattern, replacement in SENSITIVE_PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def _mask_value(self, key: Any, value: Any) -> Any:
        sensitive_keys = {"password", "secret", "token", "api_key", "authorization", "key"}
        if isinstance(key, str) and any(sk in key.lower() for sk in sensitive_keys):
            return "[REDACTED]"
        if isinstance(value, str):
            return self.mask_sensitive(value)
        return value


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure root and application loggers."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Format with timestamp, level, logger name, and message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    # Avoid duplicate handlers if setup_logging is called multiple times
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]
    root_logger.setLevel(level)

    # Configure uvicorn loggers with the same filter
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(uvicorn_logger_name)
        uv_logger.handlers = [handler]
        uv_logger.setLevel(level)

    app_logger = logging.getLogger("kuru")
    app_logger.setLevel(level)
    return app_logger
