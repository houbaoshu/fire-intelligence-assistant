"""ai_tasks 数据访问。业务规则（状态机）在 TaskService，不在此层。"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_task import AITask


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, task_id: uuid.UUID) -> AITask | None:
        return self.session.get(AITask, task_id)

    def get_scoped(
        self, task_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool
    ) -> AITask | None:
        stmt = select(AITask).where(AITask.id == task_id)
        if not is_admin:
            stmt = stmt.where(AITask.created_by == user_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_scoped(
        self,
        user_id: uuid.UUID,
        is_admin: bool,
        status: str | None,
        limit: int,
    ) -> tuple[list[AITask], int]:
        stmt = select(AITask)
        if not is_admin:
            stmt = stmt.where(AITask.created_by == user_id)
        if status is not None:
            stmt = stmt.where(AITask.status == status)
        total = self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(stmt.order_by(AITask.created_at.desc()).limit(limit))
            .scalars()
            .all()
        )
        return list(rows), total

    def has_active_of_type(self, task_type: str) -> bool:
        stmt = select(func.count()).select_from(AITask).where(
            AITask.task_type == task_type,
            AITask.status.in_(("pending", "queued", "processing")),
        )
        return self.session.execute(stmt).scalar_one() > 0

    def add(self, task: AITask) -> AITask:
        self.session.add(task)
        self.session.flush()
        return task
