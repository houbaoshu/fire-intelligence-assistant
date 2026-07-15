from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.api.routers import (
    auth,
    enterprise,
    health,
    knowledge,
    platform,
    records,
    statistics,
    system,
    tasks,
)
from app.core.config import Settings, get_settings, resolve_auth_secret
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db.session import create_database_engine, create_session_factory
from app.services.storage import LocalStorageProvider
from app.services.tasks import TaskDispatcher
from app.services.workflows import register_workflows

logger = logging.getLogger("fire_intelligence.api")


def error_response(
    *, status_code: int, code: str, message: str, details: Any = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {"code": code, "message": message, "details": details},
        },
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)
    engine = create_database_engine(resolved.database_url)
    storage = LocalStorageProvider(resolved.storage_root)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        storage.initialize()
        dispatcher: TaskDispatcher = app.state.task_dispatcher
        recovered = dispatcher.recover_pending()
        if recovered:
            logger.info("tasks.recovered", extra={"count": recovered})
        yield
        dispatcher.shutdown()
        engine.dispose()

    application = FastAPI(
        title=resolved.name,
        version=resolved.version,
        debug=resolved.debug,
        lifespan=lifespan,
    )
    application.state.settings = resolved
    application.state.signing_key = resolve_auth_secret(resolved)
    application.state.engine = engine
    application.state.session_factory = create_session_factory(engine)
    application.state.storage = storage
    application.state.request_metrics = {"requests": 0, "errors": 0, "duration_ms": 0.0}
    dispatcher = TaskDispatcher(
        application.state.session_factory, application.state, resolved.task_workers
    )
    register_workflows(dispatcher)
    application.state.task_dispatcher = dispatcher

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
        expose_headers=["X-Request-ID"],
    )

    @application.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        metrics = application.state.request_metrics
        metrics["requests"] += 1
        metrics["duration_ms"] += duration_ms
        if response.status_code >= 500:
            metrics["errors"] += 1
        logger.info(
            "request.complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @application.exception_handler(AppError)
    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        return error_response(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            details=error.details,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(value) for value in issue["loc"]), "message": issue["msg"]}
            for issue in error.errors()
        ]
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="The request contains invalid data.",
            details=details,
        )

    @application.exception_handler(HTTPException)
    async def handle_http_error(_: Request, error: HTTPException) -> JSONResponse:
        return error_response(
            status_code=error.status_code,
            code=f"HTTP_{error.status_code}",
            message=str(error.detail),
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception(
            "request.failed",
            extra={"request_id": getattr(request.state, "request_id", None)},
        )
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="An unexpected server error occurred.",
        )

    application.include_router(health.router)
    application.include_router(auth.router, prefix=resolved.api_prefix)
    application.include_router(records.router, prefix=resolved.api_prefix)
    application.include_router(tasks.router, prefix=resolved.api_prefix)
    application.include_router(knowledge.router, prefix=resolved.api_prefix)
    application.include_router(statistics.router, prefix=resolved.api_prefix)
    application.include_router(enterprise.router, prefix=resolved.api_prefix)
    application.include_router(platform.router, prefix=resolved.api_prefix)
    application.include_router(system.router, prefix=resolved.api_prefix)
    return application


app = create_app()
