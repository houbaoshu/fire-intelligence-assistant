"""Organization and Department schema definitions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganizationResponse(BaseModel):
    """Response body for organization endpoints."""

    id: str = Field(..., description="Organization UUID")
    name: str = Field(..., description="Organization name")
    code: str | None = Field(None, description="Organization code")
    address: str | None = Field(None, description="Organization address")
    contact_phone: str | None = Field(None, description="Contact phone number")
    is_active: bool = Field(..., description="Whether the organization is active")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class OrganizationCreate(BaseModel):
    """Request body for creating an organization."""

    name: str = Field(..., min_length=1, max_length=200, description="Organization name")
    code: str | None = Field(None, max_length=50, description="Organization code")
    address: str | None = Field(None, max_length=500, description="Organization address")
    contact_phone: str | None = Field(None, max_length=50, description="Contact phone number")


class OrganizationUpdate(BaseModel):
    """Request body for updating an organization."""

    name: str | None = Field(None, min_length=1, max_length=200, description="Organization name")
    code: str | None = Field(None, max_length=50, description="Organization code")
    address: str | None = Field(None, max_length=500, description="Organization address")
    contact_phone: str | None = Field(None, max_length=50, description="Contact phone number")
    is_active: bool | None = Field(None, description="Whether the organization is active")


class DepartmentResponse(BaseModel):
    """Response body for department endpoints."""

    id: str = Field(..., description="Department UUID")
    organization_id: str = Field(..., description="Parent organization UUID")
    name: str = Field(..., description="Department name")
    parent_id: str | None = Field(None, description="Parent department UUID")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class DepartmentCreate(BaseModel):
    """Request body for creating a department."""

    name: str = Field(..., min_length=1, max_length=200, description="Department name")
    parent_id: str | None = Field(None, description="Parent department UUID for nested departments")
