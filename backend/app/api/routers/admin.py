"""企业管理路由（API.md §11）。保持薄：解析请求、调用 AdminService。

全部端点按权限码授权：admin.orgs / admin.users / admin.permissions / admin.audit。
"""

import uuid

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import DbSession, get_request_id, require_permission
from app.models.user import User
from app.schemas.admin import (
    AdminUserItem,
    AdminUserUpdateRequest,
    AuditLogItem,
    DeleteResponse,
    DepartmentCreateRequest,
    DepartmentItem,
    DepartmentUpdateRequest,
    OrganizationCreateRequest,
    OrganizationItem,
    OrganizationUpdateRequest,
    PermissionItem,
    PermissionMatrixResponse,
    RolePermissionsResponse,
    RolePermissionsUpdateRequest,
)
from app.schemas.common import Page
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])

OrgsUser = Depends(require_permission("admin.orgs"))
UsersAdmin = Depends(require_permission("admin.users"))
PermsAdmin = Depends(require_permission("admin.permissions"))
AuditAdmin = Depends(require_permission("admin.audit"))


def _to_org_item(org) -> OrganizationItem:
    return OrganizationItem(
        id=org.id,
        name=org.name,
        code=org.code,
        description=org.description,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


def _to_dept_item(dept) -> DepartmentItem:
    return DepartmentItem(
        id=dept.id,
        organization_id=dept.organization_id,
        name=dept.name,
        parent_id=dept.parent_id,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


# ---------- 组织（§11.1） ----------


@router.get("/organizations", response_model=Page[OrganizationItem])
def list_organizations(
    session: DbSession,
    current_user: User = OrgsUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[OrganizationItem]:
    rows, total = AdminService(session).list_organizations(page, page_size)
    return Page(
        items=[_to_org_item(r) for r in rows], total=total, page=page, page_size=page_size
    )


@router.post("/organizations", response_model=OrganizationItem)
def create_organization(
    payload: OrganizationCreateRequest,
    session: DbSession,
    request: Request,
    current_user: User = OrgsUser,
) -> OrganizationItem:
    org = AdminService(session).create_organization(
        current_user,
        payload,
        request_id=get_request_id(request),
        ip_address=request.client.host if request.client else None,
    )
    return _to_org_item(org)


@router.put("/organizations/{organization_id}", response_model=OrganizationItem)
def update_organization(
    organization_id: uuid.UUID,
    payload: OrganizationUpdateRequest,
    session: DbSession,
    request: Request,
    current_user: User = OrgsUser,
) -> OrganizationItem:
    org = AdminService(session).update_organization(
        current_user,
        organization_id,
        payload,
        request_id=get_request_id(request),
        ip_address=request.client.host if request.client else None,
    )
    return _to_org_item(org)


@router.delete("/organizations/{organization_id}", response_model=DeleteResponse)
def delete_organization(
    organization_id: uuid.UUID,
    session: DbSession,
    request: Request,
    current_user: User = OrgsUser,
) -> DeleteResponse:
    org = AdminService(session).delete_organization(
        current_user,
        organization_id,
        request_id=get_request_id(request),
        ip_address=request.client.host if request.client else None,
    )
    return DeleteResponse(id=org.id, deleted=True)


# ---------- 部门（§11.2） ----------


@router.get("/departments", response_model=Page[DepartmentItem])
def list_departments(
    session: DbSession,
    current_user: User = OrgsUser,
    organization_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[DepartmentItem]:
    rows, total = AdminService(session).list_departments(organization_id, page, page_size)
    return Page(
        items=[_to_dept_item(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/departments", response_model=DepartmentItem)
def create_department(
    payload: DepartmentCreateRequest,
    session: DbSession,
    request: Request,
    current_user: User = OrgsUser,
) -> DepartmentItem:
    dept = AdminService(session).create_department(
        current_user,
        payload,
        request_id=get_request_id(request),
        ip_address=request.client.host if request.client else None,
    )
    return _to_dept_item(dept)


@router.put("/departments/{department_id}", response_model=DepartmentItem)
def update_department(
    department_id: uuid.UUID,
    payload: DepartmentUpdateRequest,
    session: DbSession,
    request: Request,
    current_user: User = OrgsUser,
) -> DepartmentItem:
    dept = AdminService(session).update_department(
        current_user,
        department_id,
        payload,
        request_id=get_request_id(request),
        ip_address=request.client.host if request.client else None,
    )
    return _to_dept_item(dept)


@router.delete("/departments/{department_id}", response_model=DeleteResponse)
def delete_department(
    department_id: uuid.UUID,
    session: DbSession,
    request: Request,
    current_user: User = OrgsUser,
) -> DeleteResponse:
    dept = AdminService(session).delete_department(
        current_user,
        department_id,
        request_id=get_request_id(request),
        ip_address=request.client.host if request.client else None,
    )
    return DeleteResponse(id=dept.id, deleted=True)


# ---------- 用户（§11.3） ----------


@router.get("/users", response_model=Page[AdminUserItem])
def list_users(
    session: DbSession,
    current_user: User = UsersAdmin,
    organization_id: uuid.UUID | None = None,
    role: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[AdminUserItem]:
    rows, total = AdminService(session).list_users(organization_id, role, page, page_size)
    return Page(
        items=[AdminService.to_user_item(u) for u in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put("/users/{user_id}", response_model=AdminUserItem)
def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdateRequest,
    session: DbSession,
    request: Request,
    current_user: User = UsersAdmin,
) -> AdminUserItem:
    target = AdminService(session).update_user(
        current_user,
        user_id,
        payload,
        request_id=get_request_id(request),
        ip_address=request.client.host if request.client else None,
    )
    return AdminService.to_user_item(target)


# ---------- 权限矩阵（§11.4） ----------


@router.get("/permissions", response_model=PermissionMatrixResponse)
def get_permissions(
    session: DbSession, current_user: User = PermsAdmin
) -> PermissionMatrixResponse:
    permissions, matrix = AdminService(session).get_matrix()
    return PermissionMatrixResponse(
        permissions=[
            PermissionItem(code=p.code, name=p.name, description=p.description)
            for p in permissions
        ],
        matrix=matrix,
    )


@router.put("/permissions/{role}", response_model=RolePermissionsResponse)
def update_role_permissions(
    role: str,
    payload: RolePermissionsUpdateRequest,
    session: DbSession,
    request: Request,
    current_user: User = PermsAdmin,
) -> RolePermissionsResponse:
    return AdminService(session).update_role_permissions(
        current_user,
        role,
        payload.permission_codes,
        request_id=get_request_id(request),
        ip_address=request.client.host if request.client else None,
    )


# ---------- 审计日志（§11.5） ----------


@router.get("/audit-logs", response_model=Page[AuditLogItem])
def list_audit_logs(
    session: DbSession,
    current_user: User = AuditAdmin,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[AuditLogItem]:
    rows, total = AdminService(session).list_audit_logs(
        user_id, action, entity_type, page, page_size
    )
    return Page(
        items=[
            AuditLogItem(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                request_id=log.request_id,
                ip_address=log.ip_address,
                details=log.details,
                created_at=log.created_at,
            )
            for log in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
