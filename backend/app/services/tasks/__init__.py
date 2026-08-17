"""异步任务子系统：TaskService + 执行器（ARCHITECTURE.md §9）。

执行器为进程级单例，在 FastAPI lifespan 中初始化（见 app/main.py）；
M5 以 Redis 队列实现同一抽象替换进程内执行器。
"""

from app.services.tasks.executor import (
    InProcessTaskExecutor,
    TaskExecutor,
    create_task_executor,
)
from app.services.tasks.task_service import TaskService

_executor: TaskExecutor | None = None


def set_task_executor(executor: TaskExecutor) -> None:
    global _executor
    _executor = executor


def get_task_executor() -> TaskExecutor:
    if _executor is None:
        # 测试或未走 lifespan 的场景兜底（与 lifespan 行为一致）
        set_task_executor(create_task_executor())
        assert _executor is not None
    return _executor


def shutdown_task_executor() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown()
        _executor = None


__all__ = [
    "InProcessTaskExecutor",
    "TaskExecutor",
    "TaskService",
    "create_task_executor",
    "get_task_executor",
    "set_task_executor",
    "shutdown_task_executor",
]
