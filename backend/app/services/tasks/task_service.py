"""异步任务业务逻辑（API.md §8）。router 保持薄，状态机规则收敛于此。"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import conflict, not_found
from app.models.ai_task import (
    CANCELLABLE_STATUSES,
    RETRYABLE_STATUSES,
    AITask,
)
from app.models.base import utc_now
from app.models.inspection import InspectionRecord
from app.models.interview import InterviewRecord
from app.models.photo_report import PhotoReport
from app.models.user import AuditLog, User
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import AuditLogRepository
from app.services.notification_service import notify_task_terminal
from app.services.tasks.executor import TaskExecutor
from app.services.tasks.state_machine import transition

_RECORD_MODELS = {
    "inspection_record": InspectionRecord,
    "photo_report": PhotoReport,
    "interview_record": InterviewRecord,
}


class TaskService:
    def __init__(self, session: Session, executor: TaskExecutor) -> None:
        self.session = session
        self.tasks = TaskRepository(session)
        self.audit = AuditLogRepository(session)
        self.executor = executor

    @staticmethod
    def _is_admin(user: User) -> bool:
        return user.role == "admin"

    def get(self, task_id: uuid.UUID, user: User) -> AITask:
        """任务不存在或无权限一律 404（不暴露他人任务存在性）。"""
        task = self.tasks.get_scoped(task_id, user.id, self._is_admin(user))
        if task is None:
            raise not_found("任务不存在")
        return task

    def list(self, user: User, status: str | None, limit: int) -> tuple[list[AITask], int]:
        return self.tasks.list_scoped(user.id, self._is_admin(user), status, limit)

    def retry(
        self, task_id: uuid.UUID, user: User, request_id: str | None = None
    ) -> AITask:
        """仅 failed/cancelled 可重试；重试创建新任务实例，原任务保留审计。

        新实例 attempt_count 递增并把原任务 id 记入 input_data.retry_of；
        达到 max_attempts 后再次失败即死信（RETRY_EXHAUSTED，见 tasks/execution.py）。
        """
        original = self.get(task_id, user)
        if original.status not in RETRYABLE_STATUSES:
            raise conflict(
                "TASK_STATE_CONFLICT",
                f"当前状态 {original.status} 不允许重试（仅 failed/cancelled 可重试）",
            )
        self._guard_finalized_record(original)

        input_data = dict(original.input_data or {})
        input_data["retry_of"] = str(original.id)
        new_task = AITask(
            task_type=original.task_type,
            status="pending",
            input_data=input_data,
            attempt_count=original.attempt_count + 1,
            max_attempts=original.max_attempts,
            created_by=user.id,
        )
        self.tasks.add(new_task)
        self.audit.append(
            AuditLog(
                user_id=user.id,
                action="task.retry",
                entity_type="ai_task",
                entity_id=original.id,
                request_id=request_id,
                details={
                    "new_task_id": str(new_task.id),
                    "attempt_count": new_task.attempt_count,
                },
            )
        )
        self.session.commit()
        self.session.refresh(new_task)
        self.executor.submit(new_task.id)
        return new_task

    def cancel(
        self, task_id: uuid.UUID, user: User, request_id: str | None = None
    ) -> AITask:
        """仅 pending/queued/processing 可取消；取消为尽力而为。

        先向执行器发取消信号（置位标记 + 尝试撤销未启动任务），随后调和状态：
        进程内执行器在阶段边界检查标记后自行退出，此处直接落终态。
        """
        task = self.get(task_id, user)
        if task.status not in CANCELLABLE_STATUSES:
            raise conflict(
                "TASK_STATE_CONFLICT",
                f"当前状态 {task.status} 不允许取消（仅 pending/queued/processing 可取消）",
            )
        self.executor.request_cancel(task.id)
        transition(task, "cancelled", actor="user")
        task.completed_at = utc_now()
        task.lease_expires_at = None
        notify_task_terminal(self.session, task)
        self.audit.append(
            AuditLog(
                user_id=user.id,
                action="task.cancel",
                entity_type="ai_task",
                entity_id=task.id,
                request_id=request_id,
            )
        )
        self.session.commit()
        self.session.refresh(task)
        return task

    def _guard_finalized_record(self, task: AITask) -> None:
        """重试不得静默重复生成已定稿的业务记录（API.md §8）。"""
        data = task.input_data or {}
        model = _RECORD_MODELS.get(data.get("record_kind") or "")
        record_id = data.get("record_id")
        if model is None or not record_id:
            return
        record = self.session.get(model, uuid.UUID(record_id))
        if record is not None and record.status == "finalized":
            raise conflict(
                "TASK_STATE_CONFLICT", "关联业务记录已定稿，禁止重复生成"
            )
