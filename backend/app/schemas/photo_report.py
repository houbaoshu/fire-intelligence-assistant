"""Photo report schema definitions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PhotoReportImageSchema(BaseModel):
    """Schema for a single image within a photo report."""

    id: str = Field(..., description="Image record UUID")
    photo_report_id: str = Field(..., description="Parent photo report UUID")
    frame_timestamp: float | None = Field(
        None, ge=0, description="Source video timestamp in seconds"
    )
    caption: str | None = Field(None, description="Editable image caption")
    detected_address: str | None = Field(None, description="Address recognized from the image")
    detected_violation: str | None = Field(None, description="Violation recognized from the image")
    is_selected: bool = Field(
        ..., description="Whether the image is included in the final document"
    )
    sort_order: int = Field(0, ge=0, description="Display order")

    model_config = ConfigDict(from_attributes=True)


class PhotoReportResponse(BaseModel):
    """Response body for GET /api/photo-report/{id}."""

    id: str = Field(..., description="Photo report UUID")
    title: str | None = Field(None, description="Report title")
    inspection_unit: str | None = Field(None, description="Inspected organization")
    inspection_address: str | None = Field(None, description="Inspection address")
    violation_summary: str | None = Field(None, description="Summary of detected violations")
    status: str = Field(..., description="Report status")
    source_task_id: str | None = Field(None, description="AI task that generated this report")
    images: list[PhotoReportImageSchema] = Field(default_factory=list, description="Report images")
    created_by: str = Field(..., description="UUID of the creating user")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class PhotoReportImageUpdate(BaseModel):
    """Schema for updating a single image within a photo report update request."""

    id: str = Field(..., description="Image record UUID")
    caption: str | None = Field(None, description="Updated caption")
    detected_address: str | None = Field(None, description="Updated detected address")
    detected_violation: str | None = Field(None, description="Updated detected violation")
    is_selected: bool | None = Field(None, description="Updated selection state")
    sort_order: int | None = Field(None, ge=0, description="Updated display order")


class PhotoReportUpdate(BaseModel):
    """Request body for PUT /api/photo-report/{id}.

    All fields are optional; only provided fields are updated.
    """

    title: str | None = Field(None, description="Report title")
    inspection_unit: str | None = Field(None, description="Inspected organization")
    inspection_address: str | None = Field(None, description="Inspection address")
    violation_summary: str | None = Field(None, description="Summary of detected violations")
    status: str | None = Field(None, description="Report status")
    images: list[PhotoReportImageUpdate] | None = Field(None, description="Updated image list")
