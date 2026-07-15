"""Structured logging configuration for the Fire Intelligence Platform.

Provides JSON-like structured log output with standard fields:
timestamp, level, module, and operation.  Sensitive data such as
passwords and tokens is never included in log records.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    # Keys that must NEVER appear in log output.
    _SENSITIVE_KEYS: set[str] = {
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "session_id",
    }

    def format(self, record: logging.LogRecord) -> str:
        operation = getattr(record, "operation", None)
        extra_data: dict[str, Any] = getattr(record, "extra_data", {})

        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        if operation:
            payload["operation"] = operation
        if extra_data:
            payload["data"] = self._sanitize(extra_data)
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)

    @classmethod
    def _sanitize(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive keys from *data* (non-recursive, top-level)."""
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            if key.lower() in cls._SENSITIVE_KEYS:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        return sanitized


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with structured JSON output.

    Parameters
    ----------
    level:
        Logging level name (e.g. ``"DEBUG"``, ``"INFO"``).
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any pre-existing handlers to avoid duplicate output.
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(root.level)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)

    # Quiet noisy third-party loggers.
    for name in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the given *name*.

    Usage::

        logger = get_logger(__name__)
        logger.info("Operation started", extra={"operation": "upload"})
    """
    return logging.getLogger(name)
