"""异步任务 schema（API.md §8）。"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import UTCModel


class TaskResponse(UTCModel):
    task_id: uuid.UUID
    task_type: str
    status: str
    progress: int
    current_stage: str | None
    result_data: dict | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(UTCModel):
    items: list[TaskResponse]
    total: int


class TaskRetryResponse(BaseModel):
    task_id: uuid.UUID


class TaskCancelResponse(BaseModel):
    task_id: uuid.UUID
    status: str
