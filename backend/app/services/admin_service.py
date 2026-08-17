"""企业管理业务逻辑（API.md §11）。router 保持薄，规则收敛于此。

所有管理性变更（组织/部门/用户/权限矩阵）写审计日志；审计只追加。
"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import AppException, conflict, not_found
from app.models.organization import Department, Organization
from app.models.user import USER_ROLES, AuditLog, User, utc_now
from app.repositories.organization_repository import (
    DepartmentRepository,
    OrganizationRepository,
    PermissionRepository,
)
from app.repositories.user_repository import AuditLogRepository, UserRepository
from app.schemas.admin import (
    AdminUserItem,
    AdminUserUpdateRequest,
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    RolePermissionsResponse,
)
from app.services.permission_service import ADMIN_PERMISSION_PREFIX, PermissionService


class AdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.organizations = OrganizationRepository(session)
        self.departments = DepartmentRepository(session)
        self.permissions = PermissionRepository(session)
        self.permission_service = PermissionService(session)
        self.users = UserRepository(session)
        self.audit = AuditLogRepository(session)

    # ---------- 组织 ----------

    def list_organizations(self, page: int, page_size: int):
        return self.organizations.list(page, page_size)

    def create_organization(
        self,
        actor: User,
        payload: OrganizationCreateRequest,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> Organization:
        if self.organizations.code_exists(payload.code):
            raise conflict("ORGANIZATION_CODE_EXISTS", "组织编码已存在")
        organization = Organization(
            name=payload.name, code=payload.code, description=payload.description
        )
        self.organizations.add(organization)
        self._audit(
            actor,
            "admin.organization.create",
            "organization",
            organization.id,
            request_id,
            ip_address,
            details={"name": organization.name, "code": organization.code},
        )
        self.session.commit()
        self.session.refresh(organization)
        return organization

    def update_organization(
        self,
        actor: User,
        organization_id: uuid.UUID,
        payload: OrganizationUpdateRequest,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> Organization:
        organization = self.organizations.get_by_id(organization_id)
        if organization is None:
            raise not_found("组织不存在")
        data = payload.model_dump(exclude_unset=True)
        if "code" in data and self.organizations.code_exists(
            data["code"], exclude_id=organization.id
        ):
            raise conflict("ORGANIZATION_CODE_EXISTS", "组织编码已存在")
        for field_name, value in data.items():
            setattr(organization, field_name, value)
        self._audit(
            actor,
            "admin.organization.update",
            "organization",
            organization.id,
            request_id,
            ip_address,
            details={"changes": _jsonable(data)},
        )
        self.session.commit()
        self.session.refresh(organization)
        return organization

    def delete_organization(
        self,
        actor: User,
        organization_id: uuid.UUID,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> Organization:
        organization = self.organizations.get_by_id(organization_id)
        if organization is None:
            raise not_found("组织不存在")
        if self.users.count_by_organization(organization_id) > 0:
            raise conflict("ORGANIZATION_HAS_USERS", "组织下仍有用户，无法删除")
        organization.deleted_at = utc_now()
        self._audit(
            actor,
            "admin.organization.delete",
            "organization",
            organization.id,
            request_id,
            ip_address,
        )
        self.session.commit()
        return organization

    # ---------- 部门 ----------

    def list_departments(
        self, organization_id: uuid.UUID | None, page: int, page_size: int
    ):
        return self.departments.list(organization_id, page, page_size)

    def create_department(
        self,
        actor: User,
        payload: DepartmentCreateRequest,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> Department:
        if self.organizations.get_by_id(payload.organization_id) is None:
            raise AppException("VALIDATION_ERROR", "所属组织不存在", 400)
        if payload.parent_id is not None:
            parent = self.departments.get_by_id(payload.parent_id)
            if parent is None or parent.organization_id != payload.organization_id:
                raise AppException(
                    "VALIDATION_ERROR", "上级部门不存在或不属于同一组织", 400
                )
        department = Department(
            organization_id=payload.organization_id,
            name=payload.name,
            parent_id=payload.parent_id,
        )
        self.departments.add(department)
        self._audit(
            actor,
            "admin.department.create",
            "department",
            department.id,
            request_id,
            ip_address,
            details={"name": department.name},
        )
        self.session.commit()
        self.session.refresh(department)
        return department

    def update_department(
        self,
        actor: User,
        department_id: uuid.UUID,
        payload: DepartmentUpdateRequest,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> Department:
        department = self.departments.get_by_id(department_id)
        if department is None:
            raise not_found("部门不存在")
        data = payload.model_dump(exclude_unset=True)
        if "parent_id" in data:
            parent_id = data["parent_id"]
            if parent_id is not None:
                if parent_id == department.id:
                    raise AppException("VALIDATION_ERROR", "上级部门不能是自身", 400)
                parent = self.departments.get_by_id(parent_id)
                if parent is None or parent.organization_id != department.organization_id:
                    raise AppException(
                        "VALIDATION_ERROR", "上级部门不存在或不属于同一组织", 400
                    )
        for field_name, value in data.items():
            setattr(department, field_name, value)
        self._audit(
            actor,
            "admin.department.update",
            "department",
            department.id,
            request_id,
            ip_address,
            details={"changes": _jsonable(data)},
        )
        self.session.commit()
        self.session.refresh(department)
        return department

    def delete_department(
        self,
        actor: User,
        department_id: uuid.UUID,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> Department:
        department = self.departments.get_by_id(department_id)
        if department is None:
            raise not_found("部门不存在")
        if self.users.count_by_department(department_id) > 0:
            raise conflict("DEPARTMENT_HAS_USERS", "部门下仍有用户，无法删除")
        department.deleted_at = utc_now()
        self._audit(
            actor,
            "admin.department.delete",
            "department",
            department.id,
            request_id,
            ip_address,
        )
        self.session.commit()
        return department

    # ---------- 用户 ----------

    def list_users(
        self,
        organization_id: uuid.UUID | None,
        role: str | None,
        page: int,
        page_size: int,
    ):
        if role is not None and role not in USER_ROLES:
            raise AppException("VALIDATION_ERROR", f"非法角色: {role}", 400)
        return self.users.list_admin(organization_id, role, page, page_size)

    def update_user(
        self,
        actor: User,
        user_id: uuid.UUID,
        payload: AdminUserUpdateRequest,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> User:
        target = self.users.get_by_id(user_id)
        if target is None:
            raise not_found("用户不存在")
        data = payload.model_dump(exclude_unset=True)

        if "role" in data and data["role"] not in USER_ROLES:
            raise AppException("VALIDATION_ERROR", f"非法角色: {data['role']}", 400)

        # 自锁保护：禁止把自己停用或降权（API.md §11.3）
        if target.id == actor.id:
            if data.get("is_active") is False:
                raise conflict("SELF_LOCKOUT_FORBIDDEN", "不能停用当前登录的管理员账号")
            if "role" in data and data["role"] != "admin":
                raise conflict("SELF_LOCKOUT_FORBIDDEN", "不能降低当前登录的管理员角色")

        # 组织/部门一致性：提交值优先，未提交取当前值；显式 null 表示清除
        new_org_id = data.get("organization_id", target.organization_id)
        new_dept_id = data.get("department_id", target.department_id)
        if new_org_id is not None and self.organizations.get_by_id(new_org_id) is None:
            raise AppException("VALIDATION_ERROR", "所属组织不存在", 400)
        if new_dept_id is not None:
            department = self.departments.get_by_id(new_dept_id)
            if department is None:
                raise AppException("VALIDATION_ERROR", "所属部门不存在", 400)
            if department.organization_id != new_org_id:
                raise AppException(
                    "VALIDATION_ERROR", "部门必须属于用户所属组织", 400
                )

        for field_name, value in data.items():
            setattr(target, field_name, value)
        self._audit(
            actor,
            "admin.user.update",
            "user",
            target.id,
            request_id,
            ip_address,
            details={"changes": _jsonable(data)},
        )
        self.session.commit()
        self.session.refresh(target)
        return target

    # ---------- 权限矩阵 ----------

    def get_matrix(self) -> tuple[list, dict[str, list[str]]]:
        return self.permissions.list_permissions(), self.permission_service.matrix()

    def update_role_permissions(
        self,
        actor: User,
        role: str,
        codes: list[str],
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> RolePermissionsResponse:
        if role not in USER_ROLES:
            raise AppException("VALIDATION_ERROR", f"非法角色: {role}", 400)
        unknown = sorted(set(codes) - self.permissions.known_codes())
        if unknown:
            raise AppException(
                "VALIDATION_ERROR", f"未知权限码: {', '.join(unknown)}", 400
            )
        # 防锁死：admin 角色的 admin.* 权限不可移除
        if role == "admin":
            missing = [
                code
                for code in self.permissions.known_codes()
                if code.startswith(ADMIN_PERMISSION_PREFIX) and code not in codes
            ]
            if missing:
                raise conflict(
                    "ADMIN_PERMISSION_LOCKED",
                    f"不允许移除 admin 的管理权限: {', '.join(sorted(missing))}",
                )
        self.permissions.replace_role_codes(role, codes)
        self._audit(
            actor,
            "admin.permission.update",
            "role",
            None,
            request_id,
            ip_address,
            details={"role": role, "permission_codes": sorted(set(codes))},
        )
        self.session.commit()
        return RolePermissionsResponse(
            role=role, permission_codes=self.permission_service.codes_for_role(role)
        )

    # ---------- 审计日志 ----------

    def list_audit_logs(
        self,
        user_id: uuid.UUID | None,
        action: str | None,
        entity_type: str | None,
        page: int,
        page_size: int,
    ):
        return self.audit.list_admin(user_id, action, entity_type, page, page_size)

    # ---------- 内部 ----------

    def _audit(
        self,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None,
        request_id: str | None,
        ip_address: str | None,
        details: dict | None = None,
    ) -> None:
        self.audit.append(
            AuditLog(
                user_id=actor.id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                request_id=request_id,
                ip_address=ip_address,
                details=details,
            )
        )

    @staticmethod
    def to_user_item(user: User) -> AdminUserItem:
        return AdminUserItem(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.profile.full_name if user.profile else None,
            role=user.role,
            is_active=user.is_active,
            organization_id=user.organization_id,
            department_id=user.department_id,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )


def _jsonable(data: dict) -> dict:
    return {key: str(value) if isinstance(value, uuid.UUID) else value
            for key, value in data.items()}
