"""In-process task worker.

A daemon thread polls the database for queued tasks and executes their
registered handlers. Handlers run in worker threads, never in the API event
loop (FastAPI sync endpoints already run in a threadpool; heavy AI work
happens here so HTTP requests never block on model inference).

Production deployments can run the same worker as a separate process via
`python -m app.worker`; the queue semantics stay identical.
"""
from __future__ import annotations

import threading
import time

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.tasks.registry import TaskContext, get_handler
from app.services.tasks.task_service import TaskService

logger = get_logger("tasks.worker")


class TaskWorker:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._recover_stale_tasks()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="task-worker", daemon=True)
        self._thread.start()
        logger.info("task worker started")

    def _recover_stale_tasks(self) -> None:
        """Requeue tasks stuck in 'processing' (worker crashed mid-run).

        A task whose started_at is older than the stale threshold is assumed
        orphaned; requeueing it (bounded by attempt count) keeps the pipeline
        moving without silently duplicating completed work.
        """
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import select

        from app.models.task import AiTask

        settings = get_settings()
        threshold = datetime.now(timezone.utc) - timedelta(minutes=settings.TASK_STALE_MINUTES)
        db = self.session_factory()
        try:
            stale = list(
                db.scalars(
                    select(AiTask).where(
                        AiTask.status == "processing",
                        AiTask.started_at.is_not(None),
                        AiTask.started_at < threshold,
                    )
                ).all()
            )
            for task in stale:
                if task.attempt >= settings.TASK_MAX_RETRIES:
                    task.status = "failed"
                    task.error_code = "STALE_TASK_EXHAUSTED"
                    task.error_message = "任务执行超时且重试次数已达上限"
                else:
                    task.status = "queued"
                    logger.warning("requeue stale task %s (attempt %d)", task.id, task.attempt)
            if stale:
                db.commit()
        finally:
            db.close()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        settings = get_settings()
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:  # worker must survive transient errors
                logger.exception("task worker tick failed")
            self._stop.wait(settings.TASK_POLL_INTERVAL_SECONDS)

    def _tick(self) -> None:
        db = self.session_factory()
        try:
            task = TaskService(db).claim_next()
            if task is None:
                return
            task_id, task_type = task.id, task.task_type
            logger.info("claim task %s (%s)", task_id, task_type)
        finally:
            db.close()

        handler = get_handler(task_type)
        if handler is None:
            db = self.session_factory()
            try:
                TaskService(db).mark_failed(
                    task_id, "UNKNOWN_TASK_TYPE", f"未知任务类型:{task_type}"
                )
                db.commit()
            finally:
                db.close()
            return

        db = self.session_factory()
        try:
            ctx = TaskContext(
                task_id=task_id,
                task_type=task_type,
                user_id=task.created_by,
                input_data=task.input_data or {},
                db=db,
                attempt=task.attempt,
            )
            handler(ctx)
            # handler returned without error: finalize the task unless the
            # handler already moved it to a terminal state
            svc = TaskService(db)
            current = svc.get(task_id)
            if current.status == "processing":
                svc.mark_completed(task_id, current.result_data)
            db.commit()
        except Exception as exc:  # noqa: BLE001 - fail the task, keep worker alive
            logger.exception("task %s failed: %s", task_id, exc)
            db.rollback()
            try:
                TaskService(db).mark_failed(
                    task_id, "TASK_EXECUTION_ERROR", _safe_message(exc)
                )
                db.commit()
            except Exception:  # pragma: no cover
                logger.exception("failed to persist task failure")
        finally:
            db.close()


def _safe_message(exc: Exception) -> str:
    text = str(exc) or exc.__class__.__name__
    return text[:500]
