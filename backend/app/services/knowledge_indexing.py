"""knowledge_indexing / knowledge_reindexing 任务执行体。

与 tasks/worker.py 同模式：processing → completed / failed / cancelled，
进度单调不减，取消为尽力而为（阶段边界检查标记）。同时维护
knowledge_documents 状态机与 knowledge_index_jobs 落库。

M5：状态变更统一经转移表（tasks/state_machine.py）；认领/续约/死信判定
复用 tasks/execution.py 的共享助手；终态写通知。
"""

import threading
import time
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.ai_task import TERMINAL_STATUSES, AITask
from app.models.base import utc_now
from app.models.knowledge import INDEXING_STATUSES, KnowledgeDocument, KnowledgeIndexJob
from app.rag.indexing import index_document, rebuild_index
from app.repositories.knowledge_repository import KnowledgeIndexJobRepository
from app.services.notification_service import notify_task_terminal
from app.services.pipelines import TaskCancelled
from app.services.tasks.execution import (
    audit_dead_letter,
    claim_task,
    log_terminal,
    renew_lease,
    resolve_failure,
)
from app.services.tasks.state_machine import transition

logger = get_logger("knowledge.runner")

KNOWLEDGE_TASK_TYPES = ("knowledge_indexing", "knowledge_reindexing")


def run_knowledge_task(
    session: Session,
    task: AITask,
    cancel_event: threading.Event,
    *,
    worker_id: str,
) -> None:
    """执行知识库任务并落终态；供 tasks/worker.py 按 task_type 分发。"""
    jobs = KnowledgeIndexJobRepository(session)
    job = jobs.get_by_task(task.id)
    if job is None:
        # 重试产生的新任务没有关联 job（原 job 保留审计），补建一条
        action = "index" if task.task_type == "knowledge_indexing" else "full_rebuild"
        document_id = (task.input_data or {}).get("document_id")
        job = jobs.add(
            KnowledgeIndexJob(
                knowledge_document_id=uuid.UUID(document_id) if document_id else None,
                ai_task_id=task.id,
                action=action,
            )
        )

    claim_task(session, task, worker_id)
    job.status = "processing"
    session.commit()

    stage_durations: dict[str, int] = {}
    stage_started = time.monotonic()
    last_stage: str | None = None

    def report(stage: str, progress: int) -> None:
        nonlocal stage_started, last_stage
        if cancel_event.is_set():
            raise TaskCancelled()
        now = time.monotonic()
        if last_stage is not None and stage != last_stage:
            stage_durations[last_stage] = int((now - stage_started) * 1000)
        stage_started = now
        last_stage = stage
        task.progress = max(task.progress, progress)
        task.current_stage = stage
        renew_lease(task)
        session.commit()

    try:
        if task.task_type == "knowledge_indexing":
            result_data = _run_index(session, task, job, report)
        else:
            result_data = _run_rebuild(session, job, report)
        if last_stage is not None:
            stage_durations[last_stage] = int((time.monotonic() - stage_started) * 1000)
        transition(task, "completed", actor="worker")
        task.progress = 100
        task.current_stage = None
        task.completed_at = utc_now()
        task.lease_expires_at = None
        task.result_data = result_data
        job.status = "completed"
        job.completed_at = utc_now()
        notify_task_terminal(session, task)
        session.commit()
        log_terminal(task, error_code=None, stage_durations_ms=stage_durations)
    except TaskCancelled:
        session.rollback()
        _finalize_cancelled(session, task, job, stage_durations)
    except AppException as exc:
        session.rollback()
        logger.info("知识任务 %s 失败: %s %s", task.id, exc.code, exc.message)
        _finalize_failed(session, task, job, exc.code, exc.message, stage_durations)
    except Exception:
        session.rollback()
        logger.error("知识任务 %s 未预期失败", task.id, exc_info=True)
        _finalize_failed(
            session,
            task,
            job,
            "INTERNAL_ERROR",
            "任务执行失败，请重试或联系管理员",
            stage_durations,
        )


def _document_id(task: AITask) -> uuid.UUID:
    raw = (task.input_data or {}).get("document_id")
    if not raw:
        raise AppException("TASK_INPUT_INVALID", "任务缺少 document_id 输入", 500)
    return uuid.UUID(raw)


def _run_index(
    session: Session, task: AITask, job: KnowledgeIndexJob, report
) -> dict:
    document_id = _document_id(task)
    count = index_document(session, document_id, report=report)
    job.indexed_chunks = count
    return {"document_id": str(document_id)}


def _run_rebuild(session: Session, job: KnowledgeIndexJob, report) -> dict:
    result = rebuild_index(session, report=report)
    job.indexed_chunks = result["indexed_chunks"]
    failures = result["failures"]
    if failures:
        first_title, first_message = failures[0]
        raise AppException(
            "REBUILD_PARTIAL_FAILURE",
            f"{len(failures)}/{result['total']} 篇文档重建失败"
            f"（《{first_title}》：{first_message}）；"
            "其余文档保持最后可用索引，可修复后重试",
            500,
        )
    return {"document_count": result["total"], "indexed_chunks": result["indexed_chunks"]}


def _finalize_cancelled(
    session: Session,
    task: AITask,
    job: KnowledgeIndexJob,
    stage_durations: dict[str, int],
) -> None:
    task = session.get(AITask, task.id)
    if task is None or task.status in TERMINAL_STATUSES:
        return
    transition(task, "cancelled", actor="worker")
    task.completed_at = utc_now()
    task.lease_expires_at = None
    job.status = "cancelled"
    job.completed_at = utc_now()
    _reset_document_on_abort(session, task, target="uploaded")
    notify_task_terminal(session, task)
    session.commit()
    log_terminal(task, error_code=None, stage_durations_ms=stage_durations)


def _finalize_failed(
    session: Session,
    task: AITask,
    job: KnowledgeIndexJob,
    code: str,
    message: str,
    stage_durations: dict[str, int],
) -> None:
    task = session.get(AITask, task.id)
    if task is None or task.status in TERMINAL_STATUSES:
        return
    final_code, final_message, exhausted = resolve_failure(task, code, message)
    transition(task, "failed", actor="worker")
    task.error_code = final_code
    task.error_message = final_message
    task.completed_at = utc_now()
    task.lease_expires_at = None
    if exhausted:
        audit_dead_letter(session, task, code)
    job.status = "failed"
    job.error_message = final_message
    job.completed_at = utc_now()
    _reset_document_on_abort(session, task, target="failed")
    notify_task_terminal(session, task)
    session.commit()
    log_terminal(task, error_code=final_code, stage_durations_ms=stage_durations)


def _reset_document_on_abort(session: Session, task: AITask, *, target: str) -> None:
    """索引任务中止时同步文档状态（failed / 回退 uploaded）；重建任务不归属单文档。"""
    raw = (task.input_data or {}).get("document_id")
    if not raw:
        return
    document = session.get(KnowledgeDocument, uuid.UUID(raw))
    if (
        document is not None
        and document.deleted_at is None
        and document.status in INDEXING_STATUSES
    ):
        document.status = target
