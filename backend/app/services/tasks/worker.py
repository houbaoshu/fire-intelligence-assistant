"""任务执行体：在执行器线程中运行，使用独立 DB 会话（不复用请求会话）。

状态机（API.md §8 / DATABASE.md ai_tasks）：
queued/pending → processing → completed / failed / cancelled，
所有状态变更经 services/tasks/state_machine.py 的转移表校验。
进度 0–100 单次执行内单调不减；取消为尽力而为（阶段边界检查取消标记）。

M5 执行追踪：认领时写 worker_id + 租约（lease），阶段推进时续约；
达到重试上限的失败进入死信等价流程（RETRY_EXHAUSTED + 审计）；
终态写通知（NotificationService）并输出结构化日志（queue wait、
stage duration、总时长、attempt、failure code、worker identity）。
"""

import threading
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db import SessionLocal
from app.models.ai_task import TERMINAL_STATUSES, AITask
from app.models.base import utc_now
from app.models.inspection import InspectionRecord, InspectionRecordItem
from app.models.interview import InterviewRecord
from app.models.photo_report import PhotoReport, PhotoReportImage
from app.services.ai.providers import get_ai_providers
from app.services.knowledge_indexing import KNOWLEDGE_TASK_TYPES, run_knowledge_task
from app.services.notification_service import notify_task_terminal
from app.services.pipelines import (
    PIPELINES,
    PipelineContext,
    PipelineError,
    PipelineResult,
    TaskCancelled,
)
from app.services.tasks.execution import (
    audit_dead_letter,
    claim_task,
    log_terminal,
    renew_lease,
    resolve_failure,
    worker_identity,
)
from app.services.tasks.state_machine import transition

logger = get_logger("tasks.worker")

_RECORD_MODELS = {
    "inspection_record": InspectionRecord,
    "photo_report": PhotoReport,
    "interview_record": InterviewRecord,
}


def run_task(task_id: uuid.UUID, cancel_event: threading.Event) -> None:
    worker_id = worker_identity()
    session = SessionLocal()
    stage_durations: dict[str, int] = {}
    try:
        task = session.get(AITask, task_id)
        if task is None or task.status in TERMINAL_STATUSES:
            return
        if cancel_event.is_set():
            _mark_cancelled(session, task, stage_durations)
            return

        # 知识库索引/重建任务走独立执行体（不依附业务记录管线）
        if task.task_type in KNOWLEDGE_TASK_TYPES:
            run_knowledge_task(session, task, cancel_event, worker_id=worker_id)
            return

        pipeline = PIPELINES.get(task.task_type)
        if pipeline is None:
            _mark_failed(
                session,
                task,
                "TASK_TYPE_UNSUPPORTED",
                f"任务类型 {task.task_type} 暂不支持（将在后续 milestone 提供）",
                stage_durations,
            )
            return

        claim_task(session, task, worker_id)

        ctx = _build_context(task)
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
            task.progress = max(task.progress, progress)  # 单调不减
            task.current_stage = stage
            renew_lease(task)  # 阶段推进续约
            session.commit()

        result = pipeline.run(ctx, get_ai_providers(), report)
        if last_stage is not None:
            stage_durations[last_stage] = int((time.monotonic() - stage_started) * 1000)
        _apply_result(session, pipeline.record_kind, ctx.record_id, result)
        transition(task, "completed", actor="worker")
        task.progress = 100
        task.current_stage = None
        task.completed_at = utc_now()
        task.lease_expires_at = None
        task.result_data = {"record_id": str(ctx.record_id)}
        if result.warnings:
            # 部分失败的降级说明对外可见（不静默；specs/_common.md 错误处理）
            task.result_data["warnings"] = result.warnings
        notify_task_terminal(session, task)
        session.commit()
        log_terminal(task, error_code=None, stage_durations_ms=stage_durations)
    except TaskCancelled:
        session.rollback()
        _safe_finalize(session, task_id, stage_durations, _mark_cancelled)
    except PipelineError as exc:
        session.rollback()
        logger.info("任务 %s 失败: %s %s", task_id, exc.code, exc.message)
        _safe_finalize(
            session,
            task_id,
            stage_durations,
            lambda s, t, d: _mark_failed(s, t, exc.code, exc.message, d),
        )
    except Exception:
        session.rollback()
        logger.error("任务 %s 未预期失败", task_id, exc_info=True)
        _safe_finalize(
            session,
            task_id,
            stage_durations,
            lambda s, t, d: _mark_failed(
                s, t, "INTERNAL_ERROR", "任务执行失败，请重试或联系管理员", d
            ),
        )
    finally:
        session.close()


def _build_context(task: AITask) -> PipelineContext:
    data = task.input_data or {}
    return PipelineContext(
        task_id=task.id,
        record_id=uuid.UUID(data["record_id"]),
        uploaded_file_id=uuid.UUID(data["uploaded_file_id"]),
        remarks=data.get("remarks"),
    )


def _apply_result(
    session: Session, record_kind: str, record_id: uuid.UUID, result: PipelineResult
) -> None:
    """把管线结构化产出写入业务记录并置为 generated（结构化记录是事实源）。

    幂等保证：finalized 防覆盖守卫 + retry 守卫（TaskService）确保 worker
    重启/重复投递不会静默重复定稿。
    """
    model = _RECORD_MODELS[record_kind]
    record = session.get(model, record_id)
    if record is None:
        raise PipelineError("RECORD_NOT_FOUND", "关联业务记录不存在")
    if record.status == "finalized":
        raise PipelineError("RECORD_FINALIZED", "关联业务记录已定稿，禁止覆盖")
    for key, value in result.fields.items():
        if not hasattr(record, key):
            raise PipelineError("PIPELINE_RESULT_INVALID", f"管线产出包含未知字段: {key}")
        setattr(record, key, value)
    if result.items is not None and record_kind == "inspection_record":
        record.items = [InspectionRecordItem(**item) for item in result.items]
    if result.images is not None and record_kind == "photo_report":
        record.images = [PhotoReportImage(**image) for image in result.images]
    record.status = "generated"
    session.commit()


def _safe_finalize(
    session: Session,
    task_id: uuid.UUID,
    stage_durations: dict[str, int],
    finalize,
) -> None:
    """终态落库；若任务已被取消端点调和为终态则不再覆盖。"""
    task = session.get(AITask, task_id)
    if task is None or task.status in TERMINAL_STATUSES:
        return
    finalize(session, task, stage_durations)


def _mark_cancelled(
    session: Session, task: AITask, stage_durations: dict[str, int]
) -> None:
    transition(task, "cancelled", actor="worker")
    task.completed_at = utc_now()
    task.lease_expires_at = None
    notify_task_terminal(session, task)
    session.commit()
    log_terminal(task, error_code=None, stage_durations_ms=stage_durations)


def _mark_failed(
    session: Session,
    task: AITask,
    code: str,
    message: str,
    stage_durations: dict[str, int],
) -> None:
    final_code, final_message, exhausted = resolve_failure(task, code, message)
    transition(task, "failed", actor="worker")
    task.error_code = final_code
    task.error_message = final_message
    task.completed_at = utc_now()
    task.lease_expires_at = None
    if exhausted:
        audit_dead_letter(session, task, code)
    # 关联业务草稿同步置 failed，供列表/详情展示（记录仍可由用户编辑挽救）
    record_kind = (task.input_data or {}).get("record_kind")
    record_id = (task.input_data or {}).get("record_id")
    model = _RECORD_MODELS.get(record_kind or "")
    if model is not None and record_id:
        record = session.get(model, uuid.UUID(record_id))
        if record is not None and record.status == "processing":
            record.status = "failed"
    notify_task_terminal(session, task)
    session.commit()
    log_terminal(task, error_code=final_code, stage_durations_ms=stage_durations)
