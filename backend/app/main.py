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
    admin,
    auth,
    health,
    inspection_record,
    interview_record,
    knowledge,
    notifications,
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
from app.services.tasks.reaper import create_reaper

configure_logging()
logger = get_logger("main")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # 权限目录与默认矩阵幂等种子（M6）；管理员调整过的矩阵不会被覆盖
    from app.db import SessionLocal
    from app.services.permission_service import PermissionService

    with SessionLocal() as seed_session:
        PermissionService(seed_session).seed()
        seed_session.commit()
    # 进程内任务执行器（可替换为 Redis 队列实现同一抽象）
    executor = create_task_executor()
    set_task_executor(executor)
    # 卡住任务恢复：启动时先扫一次（覆盖上次进程崩溃残留），此后周期扫描
    reaper = create_reaper(executor)
    reaper.start()
    yield
    reaper.stop()
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
app.include_router(notifications.router, prefix="/api")
app.include_router(statistics.router, prefix="/api")
app.include_router(qa.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
