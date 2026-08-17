"""通知业务逻辑（API.md §10 / DATABASE.md notifications 表）。

任务进入终态时给创建者写通知。内容为可读中文，不含敏感信息：
error_message 本身即对外契约（API.md §8 要求可读、不含敏感信息）。
通知是状态派生物，任务与业务记录仍是事实来源。
"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.models.ai_task import AITask
from app.models.base import utc_now
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository

#: task_type → 可读中文标签（通知标题/正文用）
TASK_TYPE_LABELS = {
    "inspection_record_generation": "检查记录生成",
    "photo_report_generation": "拍照报告生成",
    "interview_record_generation": "询问记录生成",
    "speech_transcription": "语音转写",
    "video_analysis": "视频分析",
    "document_generation": "文书生成",
    "knowledge_indexing": "知识库索引",
    "knowledge_reindexing": "知识库重建索引",
}

_STATUS_TO_TYPE = {
    "completed": "task_completed",
    "failed": "task_failed",
    "cancelled": "task_cancelled",
}


def notify_task_terminal(session: Session, task: AITask) -> None:
    """任务进入终态时写入通知（调用方负责在同事务 commit）。

    entity 指向关联业务记录（生成类任务）或知识文档；无关联实体时指向任务本身。
    """
    notification_type = _STATUS_TO_TYPE.get(task.status)
    if notification_type is None:
        return
    label = TASK_TYPE_LABELS.get(task.task_type, task.task_type)
    if task.status == "completed":
        title = f"{label}已完成"
        body = f"您的{label}任务已完成，可前往查看生成结果。"
    elif task.status == "failed":
        title = f"{label}失败"
        detail = task.error_message or "未知错误"
        body = f"您的{label}任务失败：{detail}"
    else:
        title = f"{label}已取消"
        body = f"您的{label}任务已取消。"

    entity_type, entity_id = _resolve_entity(task)
    NotificationRepository(session).add(
        Notification(
            user_id=task.created_by,
            type=notification_type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    )


def _resolve_entity(task: AITask) -> tuple[str | None, uuid.UUID | None]:
    data = task.input_data or {}
    record_kind = data.get("record_kind")
    record_id = data.get("record_id")
    if record_kind and record_id:
        return record_kind, uuid.UUID(record_id)
    document_id = data.get("document_id")
    if document_id:
        return "knowledge_document", uuid.UUID(document_id)
    return "ai_task", task.id


class NotificationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.notifications = NotificationRepository(session)

    def list(
        self, user: User, unread_only: bool, page: int, page_size: int
    ) -> tuple[list[Notification], int, int]:
        rows, total = self.notifications.list_own(user.id, unread_only, page, page_size)
        return rows, total, self.notifications.unread_count(user.id)

    def mark_read(self, user: User, notification_id: uuid.UUID) -> Notification:
        """他人通知一律 404（不暴露存在性）；重复标记幂等。"""
        notification = self.notifications.get_own(notification_id, user.id)
        if notification is None:
            raise not_found("通知不存在")
        if notification.read_at is None:
            notification.read_at = utc_now()
            self.session.commit()
        self.session.refresh(notification)
        return notification

    def mark_all_read(self, user: User) -> int:
        updated = self.notifications.mark_all_read(user.id)
        self.session.commit()
        return updated
