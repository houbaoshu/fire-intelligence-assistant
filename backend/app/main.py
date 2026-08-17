"""FastAPI 应用入口。

- ``/health`` 公开探针；业务路由统一挂在 ``/api`` 前缀下。
- 全局异常处理器保证所有错误响应对齐 API.md §1.3 错误信封。
- 数据库 schema 由 Alembic 管理，此处不做 create_all。
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
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
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger, set_request_id
from app.services.tasks import (
    create_task_executor,
    set_task_executor,
    shutdown_task_executor,
)

configure_logging()
logger = get_logger("main")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # 进程内任务执行器（M5 以 Redis 队列实现同一抽象替换）
    set_task_executor(create_task_executor())
    yield
    shutdown_task_executor()


app = FastAPI(title="Fire Intelligence Platform API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    set_request_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(inspection_record.router, prefix="/api")
app.include_router(photo_report.router, prefix="/api")
app.include_router(interview_record.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(statistics.router, prefix="/api")
app.include_router(qa.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
