"""Admin（企业管理）请求/响应 schema，字段严格对齐 API.md §11。"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import UTCModel


class OrganizationItem(UTCModel):
    id: uuid.UUID
    name: str
    code: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=100)
    description: str | None = None


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class DepartmentItem(UTCModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class DepartmentCreateRequest(BaseModel):
    organization_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    parent_id: uuid.UUID | None = None


class DepartmentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    parent_id: uuid.UUID | None = None


class AdminUserItem(UTCModel):
    id: uuid.UUID
    email: str
    username: str | None = None
    full_name: str | None = None
    role: str
    is_active: bool
    organization_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    last_login_at: datetime | None = None
    created_at: datetime


class AdminUserUpdateRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    organization_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None


class PermissionItem(BaseModel):
    code: str
    name: str
    description: str | None = None


class PermissionMatrixResponse(BaseModel):
    permissions: list[PermissionItem]
    matrix: dict[str, list[str]]


class RolePermissionsUpdateRequest(BaseModel):
    permission_codes: list[str]


class RolePermissionsResponse(BaseModel):
    role: str
    permission_codes: list[str]


class AuditLogItem(UTCModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    request_id: str | None = None
    ip_address: str | None = None
    details: dict | None = None
    created_at: datetime


class DeleteResponse(BaseModel):
    id: uuid.UUID
    deleted: bool = True
