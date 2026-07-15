"""Inspection record schema definitions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GenerateResponse(BaseModel):
    """Response body for generation endpoints that start an async task."""

    task_id: str = Field(..., description="UUID of the created async task")


class InspectionRecordItemSchema(BaseModel):
    """Schema for a single inspection finding or violation item."""

    id: str | None = Field(None, description="Item UUID (present after persistence)")
    item_type: str = Field(
        ...,
        description="Finding type: compliant, violation, hazard, observation, recommendation",
    )
    location: str | None = Field(None, description="Location where the finding was observed")
    description: str = Field(..., min_length=1, description="Finding description")
    legal_basis: str | None = Field(None, description="Relevant legal reference")
    correction_requirement: str | None = Field(None, description="Required corrective action")
    severity: str | None = Field(None, description="Severity level: low, medium, high, critical")
    sort_order: int = Field(0, ge=0, description="Display order")

    model_config = ConfigDict(from_attributes=True)


class InspectionRecordResponse(BaseModel):
    """Response body for GET /api/inspection-record/{id}."""

    id: str = Field(..., description="Record UUID")
    record_number: str | None = Field(None, description="Business record number")
    title: str | None = Field(None, description="Record title")
    inspection_unit: str | None = Field(None, description="Inspected organization")
    inspection_address: str | None = Field(None, description="Inspection address")
    inspection_date: datetime | None = Field(None, description="Date of inspection")
    inspector_names: list[str] | None = Field(None, description="List of inspector names")
    contact_person: str | None = Field(None, description="On-site contact person")
    contact_phone: str | None = Field(None, description="On-site contact phone")
    summary: str | None = Field(None, description="Inspection summary")
    conclusion: str | None = Field(None, description="Inspection conclusion")
    status: str = Field(..., description="Record status")
    source_task_id: str | None = Field(None, description="AI task that generated this record")
    items: list[InspectionRecordItemSchema] = Field(
        default_factory=list, description="Inspection findings"
    )
    created_by: str = Field(..., description="UUID of the creating user")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class InspectionRecordUpdate(BaseModel):
    """Request body for PUT /api/inspection-record/{id}.

    All fields are optional; only provided fields are updated.
    """

    title: str | None = Field(None, description="Record title")
    inspection_unit: str | None = Field(None, description="Inspected organization")
    inspection_address: str | None = Field(None, description="Inspection address")
    inspection_date: datetime | None = Field(None, description="Date of inspection")
    inspector_names: list[str] | None = Field(None, description="List of inspector names")
    contact_person: str | None = Field(None, description="On-site contact person")
    contact_phone: str | None = Field(None, description="On-site contact phone")
    summary: str | None = Field(None, description="Inspection summary")
    conclusion: str | None = Field(None, description="Inspection conclusion")
    status: str | None = Field(None, description="Record status")
    items: list[InspectionRecordItemSchema] | None = Field(
        None, description="Full replacement list of inspection findings"
    )
