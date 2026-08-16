"""Admin endpoints (Milestone 6): users, organizations, departments, audit logs."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Header
from pydantic import BaseModel, EmailStr, Field

from app.api.dependencies import CurrentUser, DB
from app.core.exceptions import ForbiddenError
from app.services.admin_service import AdminService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/admin", tags=["admin"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None
    role: str = "inspector"
    organization_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    organization_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    full_name: str | None = None


class OrgCreate(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = None


class DeptCreate(BaseModel):
    organization_id: uuid.UUID
    name: str = Field(min_length=1)


def _user_out(u) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "full_name": u.profile.full_name if u.profile else None,
        "role": u.role,
        "is_active": u.is_active,
        "organization_id": str(u.organization_id) if u.organization_id else None,
        "department_id": str(u.department_id) if u.department_id else None,
        "last_login_at": u.last_login_at,
        "created_at": u.created_at,
    }


def _require_admin(user) -> None:
    if user.role != "admin":
        raise ForbiddenError("仅管理员可访问")


@router.get("/users")
def list_users(user: CurrentUser, db: DB, page: int = 1, page_size: int = 20, role: str | None = None):
    _require_admin(user)
    items, total = AdminService(db).list_users(page=page, page_size=page_size, role=role)
    return {"items": [_user_out(u) for u in items], "total": total, "page": page, "page_size": page_size}


@router.post("/users", status_code=201)
def create_user(user: CurrentUser, db: DB, payload: UserCreate):
    _require_admin(user)
    u = AdminService(db).create_user(
        user, email=payload.email, password=payload.password, full_name=payload.full_name,
        role=payload.role, organization_id=payload.organization_id, department_id=payload.department_id,
    )
    return _user_out(u)


@router.put("/users/{user_id}")
def update_user(user: CurrentUser, db: DB, user_id: uuid.UUID, payload: UserUpdate):
    _require_admin(user)
    u = AdminService(db).update_user(
        user, user_id,
        role=payload.role, is_active=payload.is_active,
        organization_id=payload.organization_id, department_id=payload.department_id,
        full_name=payload.full_name,
    )
    return _user_out(u)


@router.get("/organizations")
def list_orgs(user: CurrentUser, db: DB):
    _require_admin(user)
    orgs = AdminService(db).list_organizations()
    return {"items": [{"id": str(o.id), "name": o.name, "code": o.code, "description": o.description, "created_at": o.created_at} for o in orgs]}


@router.post("/organizations", status_code=201)
def create_org(user: CurrentUser, db: DB, payload: OrgCreate):
    _require_admin(user)
    org = AdminService(db).create_organization(user, name=payload.name, code=payload.code, description=payload.description)
    return {"id": str(org.id), "name": org.name, "code": org.code, "description": org.description, "created_at": org.created_at}


@router.get("/departments")
def list_depts(user: CurrentUser, db: DB, organization_id: uuid.UUID | None = None):
    _require_admin(user)
    depts = AdminService(db).list_departments(organization_id)
    return {"items": [{"id": str(d.id), "organization_id": str(d.organization_id), "name": d.name} for d in depts]}


@router.post("/departments", status_code=201)
def create_dept(user: CurrentUser, db: DB, payload: DeptCreate):
    _require_admin(user)
    d = AdminService(db).create_department(user, organization_id=payload.organization_id, name=payload.name)
    return {"id": str(d.id), "organization_id": str(d.organization_id), "name": d.name}


@router.get("/audit-logs")
def list_audit_logs(user: CurrentUser, db: DB, page: int = 1, page_size: int = 50):
    _require_admin(user)
    items, total = AdminService(db).list_audit_logs(page=page, page_size=page_size)
    return {
        "items": [
            {
                "id": str(a.id),
                "user_id": str(a.user_id) if a.user_id else None,
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": str(a.entity_id) if a.entity_id else None,
                "ip_address": a.ip_address,
                "details": a.details,
                "created_at": a.created_at,
            }
            for a in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
