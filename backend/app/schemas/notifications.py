"""通知 schema（API.md §10）。"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import UTCModel


class NotificationItem(UTCModel):
    id: uuid.UUID
    type: str
    title: str
    body: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(UTCModel):
    items: list[NotificationItem]
    total: int
    unread_count: int
    page: int
    page_size: int


class NotificationReadResponse(UTCModel):
    id: uuid.UUID
    read_at: datetime | None


class NotificationReadAllResponse(BaseModel):
    updated: int
