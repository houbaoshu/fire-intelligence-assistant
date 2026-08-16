"""Domain exceptions mapped to the unified API error envelope.

Envelope (see API.md §1.3):
    {"error": {"code": "...", "message": "...", "details": ...}}
"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error with an HTTP status and machine-readable code."""

    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: Any = None):
        super().__init__(message)
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            payload["details"] = self.details
        return payload


class ValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class FileTypeError(AppError):
    status_code = 400
    code = "INVALID_FILE_TYPE"


class FileTooLargeError(AppError):
    status_code = 413
    code = "FILE_TOO_LARGE"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class TaskStateConflictError(AppError):
    status_code = 409
    code = "TASK_STATE_CONFLICT"


class AIProviderError(AppError):
    status_code = 502
    code = "AI_PROVIDER_ERROR"


class AINotConfiguredError(AppError):
    status_code = 503
    code = "AI_NOT_CONFIGURED"


class StorageError(AppError):
    status_code = 500
    code = "STORAGE_ERROR"


class DocumentGenerationError(AppError):
    status_code = 500
    code = "DOCUMENT_GENERATION_ERROR"
