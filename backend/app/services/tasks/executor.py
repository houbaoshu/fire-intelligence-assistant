"""进程内任务执行器（开发态）。

接口为 M5 预留：M5 以 Redis 队列实现同一 ``TaskExecutor`` 抽象即可替换，
业务代码只依赖抽象（ARCHITECTURE.md §9，README「设计决策」）。
"""

import threading
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor

from app.core.logging import get_logger

logger = get_logger("tasks.executor")


class TaskExecutor(ABC):
    @abstractmethod
    def submit(self, task_id: uuid.UUID) -> None:
        """提交任务执行。"""

    @abstractmethod
    def request_cancel(self, task_id: uuid.UUID) -> None:
        """尽力而为地请求取消：置位取消标记；尚未启动的任务直接放弃。"""

    @abstractmethod
    def shutdown(self) -> None:
        """应用关闭时调用。"""


class InProcessTaskExecutor(TaskExecutor):
    def __init__(self, max_workers: int = 4) -> None:
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="ai-task"
        )
        self._lock = threading.Lock()
        self._cancel_events: dict[uuid.UUID, threading.Event] = {}
        self._futures: dict[uuid.UUID, Future] = {}

    def submit(self, task_id: uuid.UUID) -> None:
        # 延迟导入避免循环依赖（worker 依赖 models/db）
        from app.services.tasks.worker import run_task

        event = threading.Event()
        with self._lock:
            self._cancel_events[task_id] = event
        future = self._pool.submit(run_task, task_id, event)
        with self._lock:
            self._futures[task_id] = future
        future.add_done_callback(lambda _: self._cleanup(task_id))

    def request_cancel(self, task_id: uuid.UUID) -> None:
        with self._lock:
            event = self._cancel_events.get(task_id)
            future = self._futures.get(task_id)
        if event is not None:
            event.set()
        if future is not None:
            future.cancel()  # 仅在尚未启动时生效

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)

    def _cleanup(self, task_id: uuid.UUID) -> None:
        with self._lock:
            self._cancel_events.pop(task_id, None)
            self._futures.pop(task_id, None)


def create_task_executor() -> TaskExecutor:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.TASK_EXECUTOR == "in_process":
        return InProcessTaskExecutor(max_workers=settings.EXECUTOR_WORKERS)
    raise ValueError(f"不支持的任务执行器: {settings.TASK_EXECUTOR}")
