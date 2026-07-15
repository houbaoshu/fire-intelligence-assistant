"""Async task schema definitions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskResponse(BaseModel):
    """Response body for GET /api/tasks/{task_id}."""

    id: str = Field(..., description="Task UUID")
    task_type: str = Field(
        ...,
        description="Task category, e.g. inspection_record_generation, knowledge_indexing",
    )
    status: str = Field(
        ...,
        description="Task status: pending, queued, processing, completed, failed, cancelled",
    )
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    current_stage: str | None = Field(None, description="Current processing stage name")
    error_code: str | None = Field(
        None, description="Machine-readable error code (present on failure)"
    )
    error_message: str | None = Field(
        None, description="Human-readable error message (present on failure)"
    )
    started_at: datetime | None = Field(None, description="When the task started processing")
    completed_at: datetime | None = Field(None, description="When the task completed or failed")
    created_at: datetime = Field(..., description="Task creation timestamp")
    result_data: dict[str, Any] | None = Field(
        None, description="Structured result data (present on completion)"
    )

    model_config = ConfigDict(from_attributes=True)
