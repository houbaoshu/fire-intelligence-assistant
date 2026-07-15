"""Custom exception hierarchy and FastAPI exception handler registration.

All application-specific errors derive from ``AppException`` so that a
single handler can translate them into consistent JSON responses.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ── Exception classes ───────────────────────────────────────────────────────


class AppException(Exception):  # noqa: N818 - established public API name
    """Base class for all application exceptions.

    Attributes
    ----------
    status_code : int
        HTTP status code returned to the client.
    code : str
        Machine-readable error identifier.
    message : str
        Human-readable description of the error.
    details : Any
        Optional additional information (field-level errors, etc.).
    """

    status_code: int = 500
    code: str = "APP_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        details: Any = None,
    ) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundException(AppException):
    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found", details: Any = None) -> None:
        super().__init__(message, details)


class UnauthorizedException(AppException):
    status_code = 401
    code = "UNAUTHORIZED"

    def __init__(
        self,
        message: str = "Authentication required",
        details: Any = None,
    ) -> None:
        super().__init__(message, details)


class ForbiddenException(AppException):
    status_code = 403
    code = "FORBIDDEN"

    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        details: Any = None,
    ) -> None:
        super().__init__(message, details)


class ValidationException(AppException):
    status_code = 422
    code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str = "Validation failed",
        details: Any = None,
    ) -> None:
        super().__init__(message, details)


class ConflictException(AppException):
    status_code = 409
    code = "CONFLICT"

    def __init__(
        self,
        message: str = "Resource already exists",
        details: Any = None,
    ) -> None:
        super().__init__(message, details)


class TaskFailedException(AppException):
    status_code = 500
    code = "TASK_FAILED"

    def __init__(
        self,
        message: str = "Task execution failed",
        details: Any = None,
    ) -> None:
        super().__init__(message, details)


class FileValidationException(AppException):
    status_code = 422
    code = "FILE_VALIDATION_ERROR"

    def __init__(
        self,
        message: str = "File validation failed",
        details: Any = None,
    ) -> None:
        super().__init__(message, details)


# ── Handler registration ────────────────────────────────────────────────────


def _app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Translate an ``AppException`` into a JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


async def _generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler that hides internal details from the client."""
    # In production the real traceback should be written to the log,
    # not returned to the caller.
    import logging

    logger = logging.getLogger(__name__)
    logger.exception("Unhandled exception: %s", exc)

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal server error occurred",
                "details": None,
            },
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI *app*."""
    app.add_exception_handler(AppException, _app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _generic_exception_handler)  # type: ignore[arg-type]
