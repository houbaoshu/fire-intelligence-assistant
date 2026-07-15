"""Interview record schema definitions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InterviewRecordResponse(BaseModel):
    """Response body for GET /api/interview-record/{id}."""

    id: str = Field(..., description="Interview record UUID")
    title: str | None = Field(None, description="Record title")
    interviewee_name: str | None = Field(None, description="Name of the interviewed person")
    interviewer_names: list[str] | None = Field(None, description="List of interviewer names")
    location: str | None = Field(None, description="Interview location")
    started_at: datetime | None = Field(None, description="Interview start time")
    ended_at: datetime | None = Field(None, description="Interview end time")
    transcript: str | None = Field(None, description="Speech transcript text")
    structured_content: dict[str, Any] | None = Field(
        None, description="Structured interview content as JSON"
    )
    status: str = Field(..., description="Record status")
    source_task_id: str | None = Field(None, description="AI task that generated this record")
    created_by: str = Field(..., description="UUID of the creating user")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class InterviewRecordUpdate(BaseModel):
    """Request body for PUT /api/interview-record/{id}.

    All fields are optional; only provided fields are updated.
    """

    title: str | None = Field(None, description="Record title")
    interviewee_name: str | None = Field(None, description="Name of the interviewed person")
    interviewer_names: list[str] | None = Field(None, description="List of interviewer names")
    location: str | None = Field(None, description="Interview location")
    started_at: datetime | None = Field(None, description="Interview start time")
    ended_at: datetime | None = Field(None, description="Interview end time")
    transcript: str | None = Field(None, description="Speech transcript text")
    structured_content: dict[str, Any] | None = Field(
        None, description="Structured interview content as JSON"
    )
    status: str | None = Field(None, description="Record status")
