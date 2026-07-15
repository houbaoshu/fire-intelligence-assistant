"""Fire Intelligence Platform -- FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import dispose_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler: startup and shutdown."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Starting Fire Intelligence Platform API")
    logger.info("Storage provider: %s", settings.storage_provider)
    logger.info("LLM model: %s", settings.llm_model)
    yield
    logger.info("Shutting down Fire Intelligence Platform API")
    await dispose_engine()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Fire Intelligence Platform API",
        description="AI-powered fire inspection system for document generation, "
        "knowledge retrieval, and inspection assistance.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ───────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ──────────────────────────────────────────────────────────
    from app.api.routers import (
        audit as audit_router,
    )
    from app.api.routers import (
        model_management,
        organizations,
        prompts,
    )
    from app.routers import (
        auth,
        health,
        inspection_record,
        interview_record,
        knowledge,
        photo_report,
        qa,
        statistics,
        tasks,
    )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/auth")
    app.include_router(qa.router, prefix="/api/qa")
    app.include_router(inspection_record.router, prefix="/api/inspection-record")
    app.include_router(photo_report.router, prefix="/api/photo-report")
    app.include_router(interview_record.router, prefix="/api/interview-record")
    app.include_router(knowledge.router, prefix="/api/knowledge")
    app.include_router(tasks.router, prefix="/api/tasks")
    app.include_router(statistics.router, prefix="/api/statistics")
    app.include_router(organizations.router, prefix="/api/organizations")
    app.include_router(audit_router.router, prefix="/api/audit-logs")
    app.include_router(prompts.router, prefix="/api/prompts")
    app.include_router(model_management.router, prefix="/api/models")

    return app


app = create_app()
