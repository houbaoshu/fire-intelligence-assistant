"""通知路由（API.md §10）。保持薄：解析请求、调用 NotificationService。

权限：所有认证用户，只能读取与操作自己的通知（归属校验在 service/repository 层）。
"""

import uuid

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.notifications import (
    NotificationItem,
    NotificationListResponse,
    NotificationReadAllResponse,
    NotificationReadResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_item(n) -> NotificationItem:
    return NotificationItem(
        id=n.id,
        type=n.type,
        title=n.title,
        body=n.body,
        entity_type=n.entity_type,
        entity_id=n.entity_id,
        read_at=n.read_at,
        created_at=n.created_at,
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    session: DbSession,
    current_user: CurrentUser,
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> NotificationListResponse:
    rows, total, unread = NotificationService(session).list(
        current_user, unread_only, page, page_size
    )
    return NotificationListResponse(
        items=[_to_item(n) for n in rows],
        total=total,
        unread_count=unread,
        page=page,
        page_size=page_size,
    )


@router.post("/read-all", response_model=NotificationReadAllResponse)
def mark_all_read(session: DbSession, current_user: CurrentUser) -> NotificationReadAllResponse:
    updated = NotificationService(session).mark_all_read(current_user)
    return NotificationReadAllResponse(updated=updated)


@router.post("/{notification_id}/read", response_model=NotificationReadResponse)
def mark_read(
    notification_id: uuid.UUID, session: DbSession, current_user: CurrentUser
) -> NotificationReadResponse:
    notification = NotificationService(session).mark_read(current_user, notification_id)
    return NotificationReadResponse(id=notification.id, read_at=notification.read_at)
