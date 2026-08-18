"""FastAPI 应用入口。

- ``/health`` 公开探针；业务路由统一挂在 ``/api`` 前缀下。
- 全局异常处理器保证所有错误响应对齐 API.md §1.3 错误信封。
- 数据库 schema 由 Alembic 管理，此处不做 create_all。
"""

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    admin,
    agent,
    ai_platform,
    auth,
    health,
    inspection_record,
    interview_record,
    knowledge,
    metrics,
    notifications,
    photo_report,
    qa,
    statistics,
    tasks,
)
from app.core.bootstrap import run_migrations, seed_default_admin
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger, set_request_id
from app.core.metrics import get_metrics_registry
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
    # 启动自动化（M7）：自动执行 alembic upgrade head（AUTO_MIGRATE=false 可关闭），
    # 随后幂等创建默认管理员（DEFAULT_ADMIN_EMAIL / DEFAULT_ADMIN_PASSWORD）
    run_migrations()
    # 权限目录与默认矩阵幂等种子（M6）；管理员调整过的矩阵不会被覆盖
    from app.db import SessionLocal
    from app.services.permission_service import PermissionService
    from app.services.plugin_service import PluginService
    from app.services.prompt_service import PromptService

    with SessionLocal() as seed_session:
        seed_default_admin(seed_session)
        PermissionService(seed_session).seed()
        # M8：Prompt 常量幂等种子为 v1 生效版本；内置插件幂等注册
        PromptService(seed_session).seed()
        PluginService(seed_session).register_builtin()
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


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    # /metrics 自身不计入请求指标，避免自增噪音
    if request.url.path == "/metrics":
        return await call_next(request)
    started = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - started
    # 路由模板（如 /api/tasks/{task_id}）避免高基数；未匹配路由记为 unmatched。
    # 当前 FastAPI 版本惰性 include_router 后 route.path 不含 /api 前缀，按实际路径补回
    route = request.scope.get("route")
    route_template = getattr(route, "path", None) or "unmatched"
    if (
        route_template != "unmatched"
        and request.url.path.startswith("/api/")
        and not route_template.startswith("/api/")
    ):
        route_template = "/api" + route_template
    get_metrics_registry().record_http_request(
        request.method, route_template, response.status_code, duration
    )
    return response


register_exception_handlers(app)

app.include_router(health.router)
app.include_router(metrics.router)
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
app.include_router(ai_platform.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
