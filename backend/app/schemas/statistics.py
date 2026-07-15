"""Statistics schema definitions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StatisticsResponse(BaseModel):
    """Response body for GET /api/statistics."""

    inspection_records_count: int = Field(0, ge=0, description="Total inspection records")
    photo_reports_count: int = Field(0, ge=0, description="Total photo reports")
    interview_records_count: int = Field(0, ge=0, description="Total interview records")
    knowledge_documents_count: int = Field(0, ge=0, description="Total knowledge documents")
    active_tasks_count: int = Field(0, ge=0, description="Currently active AI tasks")
    generated_documents_count: int = Field(0, ge=0, description="Total generated documents")
