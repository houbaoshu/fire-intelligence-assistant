"""Async task schemas (API.md §8)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TaskOut(BaseModel):
    task_id: str
    task_type: str
    status: str
    progress: int
    current_stage: str | None = None
    result_data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskOut]
    total: int


class TaskActionResponse(BaseModel):
    task_id: str
    status: str
