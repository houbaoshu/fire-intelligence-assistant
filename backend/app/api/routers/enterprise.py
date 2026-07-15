from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.permissions import ROLE_PERMISSIONS, require_admin, require_permission
from app.db.models import (
    AuditLog,
    Department,
    Organization,
    OrganizationMembership,
    RolePermission,
    User,
)
from app.db.session import get_db
from app.schemas.business import DepartmentCreate, MembershipCreate, OrganizationCreate
from app.services.audit import add_audit_log

router = APIRouter(tags=["enterprise"])


def _serialize(value: object) -> dict[str, object]:
    return {
        column.name: getattr(value, column.name)
        for column in value.__table__.columns  # type: ignore[attr-defined]
        if column.name not in {"password_hash"}
    }


@router.get("/organizations")
def list_organizations(
    session: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[dict[str, object]]:
    return [
        _serialize(item)
        for item in session.scalars(
            select(Organization)
            .where(Organization.deleted_at.is_(None))
            .order_by(Organization.name)
        )
    ]


@router.post("/organizations", status_code=201)
def create_organization(
    payload: OrganizationCreate,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict[str, object]:
    organization = Organization(name=payload.name, slug=payload.slug)
    session.add(organization)
    session.flush()
    add_audit_log(
        session,
        user_id=user.id,
        action="organization.create",
        entity_type="organization",
        entity_id=organization.id,
        request_id=getattr(request.state, "request_id", None),
    )
    session.commit()
    return _serialize(organization)


@router.get("/departments")
def list_departments(
    organization_id: uuid.UUID,
    session: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[dict[str, object]]:
    return [
        _serialize(item)
        for item in session.scalars(
            select(Department)
            .where(Department.organization_id == organization_id)
            .order_by(Department.name)
        )
    ]


@router.post("/departments", status_code=201)
def create_department(
    payload: DepartmentCreate,
    session: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, object]:
    department = Department(**payload.model_dump())
    session.add(department)
    session.commit()
    return _serialize(department)


@router.get("/memberships")
def list_memberships(
    organization_id: uuid.UUID,
    session: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[dict[str, object]]:
    return [
        _serialize(item)
        for item in session.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id
            )
        )
    ]


@router.post("/memberships", status_code=201)
def create_membership(
    payload: MembershipCreate,
    session: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, object]:
    membership = OrganizationMembership(**payload.model_dump())
    session.add(membership)
    session.commit()
    return _serialize(membership)


@router.get("/role-permissions")
def role_permissions(
    session: Session = Depends(get_db), _: User = Depends(require_admin)
) -> dict[str, list[str]]:
    result = {role: sorted(values) for role, values in ROLE_PERMISSIONS.items()}
    rows = session.execute(select(RolePermission.role, RolePermission.permission)).all()
    configured_roles = {role for role, _ in rows}
    for role in configured_roles:
        result[role] = sorted(permission for row_role, permission in rows if row_role == role)
    return result


@router.put("/role-permissions/{role}")
def replace_role_permissions(
    role: str,
    permissions: list[str],
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict[str, list[str]]:
    if role not in ROLE_PERMISSIONS or role == "admin":
        from app.core.exceptions import AppError

        raise AppError(
            status_code=422,
            code="INVALID_ROLE",
            message="The administrator role cannot be changed and the role must be recognized.",
        )
    normalized = sorted({value for value in permissions if value and len(value) <= 100})
    session.execute(delete(RolePermission).where(RolePermission.role == role))
    session.add_all(RolePermission(role=role, permission=value) for value in normalized)
    add_audit_log(
        session,
        user_id=user.id,
        action="role_permissions.replace",
        entity_type="role",
        request_id=getattr(request.state, "request_id", None),
        details={"role": role, "permissions": normalized},
    )
    session.commit()
    return {role: normalized}


@router.get("/audit-logs")
def audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
    _: User = Depends(require_permission("audit.read")),
) -> list[dict[str, object]]:
    return [
        _serialize(item)
        for item in session.scalars(
            select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        )
    ]
