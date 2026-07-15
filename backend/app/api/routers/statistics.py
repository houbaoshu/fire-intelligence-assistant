from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import authorized_user_ids, require_permission
from app.db.models import (
    AITask,
    GeneratedDocument,
    InspectionRecord,
    InterviewRecord,
    KnowledgeDocument,
    PhotoReport,
    User,
)
from app.db.session import get_db
from app.schemas.business import Metric, StatisticsResponse

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("", response_model=StatisticsResponse)
def statistics(
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("statistics.read")),
) -> StatisticsResponse:
    visible = authorized_user_ids(session, user)

    def count(model: type[object], *, soft_delete: bool = True) -> int:
        conditions = []
        if visible is not None and hasattr(model, "created_by"):
            conditions.append(model.created_by.in_(visible))
        if soft_delete and hasattr(model, "deleted_at"):
            conditions.append(model.deleted_at.is_(None))
        return (
            session.scalar(
                select(func.count(model.id)).where(*conditions)  # type: ignore[attr-defined]
            )
            or 0
        )

    metrics = [
        Metric(id="inspection_records", label="检查记录", value=count(InspectionRecord), unit="条"),
        Metric(id="photo_reports", label="图像报告", value=count(PhotoReport), unit="份"),
        Metric(id="interview_records", label="询问笔录", value=count(InterviewRecord), unit="份"),
        Metric(
            id="generated_documents",
            label="生成文档",
            value=count(GeneratedDocument, soft_delete=False),
            unit="个",
        ),
        Metric(id="ai_tasks", label="处理任务", value=count(AITask, soft_delete=False), unit="个"),
        Metric(
            id="knowledge_documents", label="知识文档", value=count(KnowledgeDocument), unit="份"
        ),
    ]
    task_conditions = [AITask.created_by.in_(visible)] if visible is not None else []
    task_statuses = {
        status: amount
        for status, amount in session.execute(
            select(AITask.status, func.count(AITask.id))
            .where(*task_conditions)
            .group_by(AITask.status)
        )
    }
    knowledge_statuses = {
        status: amount
        for status, amount in session.execute(
            select(KnowledgeDocument.status, func.count(KnowledgeDocument.id))
            .where(
                KnowledgeDocument.deleted_at.is_(None),
                *([KnowledgeDocument.created_by.in_(visible)] if visible is not None else []),
            )
            .group_by(KnowledgeDocument.status)
        )
    }
    now = datetime.now(UTC)
    return StatisticsResponse(
        scope=(
            "system"
            if user.role == "admin"
            else "organization"
            if user.role == "supervisor"
            else "personal"
        ),
        period_start=None,
        period_end=now,
        timezone="UTC",
        last_updated_at=now,
        metrics=metrics,
        task_statuses=task_statuses,
        knowledge_statuses=knowledge_statuses,
    )
