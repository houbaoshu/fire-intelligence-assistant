"""FastAPI application factory.

Lifespan: ensure directories -> (dev) create tables -> seed admin -> start worker.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import (
    admin,
    ai_platform,
    auth,
    files,
    health,
    inspection_record,
    interview_record,
    knowledge,
    monitoring,
    photo_report,
    qa,
    statistics,
    tasks,
)
from app.core.config import get_settings
from app.core.database import SessionLocal, dispose_engine, init_db
from app.core.exceptions import AppError
from app.core.logging import get_logger, setup_logging
from app.services import handlers  # noqa: F401  (register task handlers)

logger = get_logger("app")


def _seed_admin() -> None:
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.models.user import User, UserProfile

    settings = get_settings()
    if settings.APP_ENV == "testing":
        return
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == settings.DEFAULT_ADMIN_EMAIL))
        if existing is None:
            admin = User(
                email=settings.DEFAULT_ADMIN_EMAIL,
                password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.flush()
            db.add(UserProfile(user_id=admin.id, full_name="系统管理员"))
            db.commit()
            logger.info("seeded admin user %s", settings.DEFAULT_ADMIN_EMAIL)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging()
    settings.ensure_directories()
    logger.info("starting %s (%s)", settings.APP_NAME, settings.APP_ENV)

    if settings.APP_ENV != "testing":
        if settings.DATABASE_URL.startswith("sqlite"):
            # dev bootstrap: create tables directly (migrations are still provided)
            init_db()
        # seed permission catalog + prompt catalog (idempotent)
        db = SessionLocal()
        try:
            from app.services.aiplatform.prompt_service import PromptService
            from app.services.permission_service import seed_permissions

            seed_permissions(db)
            PromptService(db).ensure_seeded()
            db.commit()
        finally:
            db.close()
        _seed_admin()

    worker = None
    if settings.TASK_WORKER_IN_PROCESS and settings.APP_ENV != "testing":
        from app.services.tasks.worker import TaskWorker

        worker = TaskWorker(SessionLocal)
        worker.start()

    yield

    if worker:
        worker.stop()
    dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()
    settings.ensure_directories()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # dev default; production restricts via env
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        import time

        from app.core import metrics

        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.monotonic()
        response = await call_next(request)
        metrics.inc_counter(
            "http_requests",
            method=request.method,
            path=request.url.path,
            status=str(response.status_code),
        )
        metrics.observe_histogram("http_request_duration_seconds", time.monotonic() - start, **{"method": request.method})
        response.headers["X-Request-Id"] = request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.to_dict()})

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        messages = []
        for d in exc.errors():
            loc = ".".join(str(x) for x in d.get("loc", []) if x != "body")
            msg = d.get("msg", "")
            messages.append(f"{loc}: {msg}" if loc else msg)
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "; ".join(messages) or "请求参数校验失败",
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误,请稍后重试"}},
        )

    # health is public and outside /api
    app.include_router(health.router)
    app.include_router(monitoring.router)
    app.include_router(auth.router, prefix=settings.API_PREFIX)
    app.include_router(inspection_record.router, prefix=settings.API_PREFIX)
    app.include_router(photo_report.router, prefix=settings.API_PREFIX)
    app.include_router(interview_record.router, prefix=settings.API_PREFIX)
    app.include_router(qa.router, prefix=settings.API_PREFIX)
    app.include_router(knowledge.router, prefix=settings.API_PREFIX)
    app.include_router(tasks.router, prefix=settings.API_PREFIX)
    app.include_router(statistics.router, prefix=settings.API_PREFIX)
    app.include_router(files.router, prefix=settings.API_PREFIX)
    app.include_router(admin.router, prefix=settings.API_PREFIX)
    app.include_router(ai_platform.router, prefix=settings.API_PREFIX)

    return app


app = create_app()
