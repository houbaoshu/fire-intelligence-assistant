"""Enterprise admin service (Milestone 6).

User management, organization/department management and audit log access.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.enums import USER_ROLES
from app.models.org import Department, Organization
from app.models.user import User, UserProfile
from app.services.audit_service import AuditService
from app.services.permission_service import PermissionService


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.permissions = PermissionService(db)
        self.audit = AuditService(db)

    # ---- users --------------------------------------------------------------

    def list_users(self, *, page: int = 1, page_size: int = 20, role: str | None = None) -> tuple[list[User], int]:
        from sqlalchemy import func

        base = select(User).where(User.deleted_at.is_(None))
        count_base = select(func.count(User.id)).where(User.deleted_at.is_(None))
        if role:
            base = base.where(User.role == role)
            count_base = count_base.where(User.role == role)
        total = int(self.db.scalar(count_base) or 0)
        items = list(
            self.db.scalars(
                base.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            ).all()
        )
        return items, total

    def create_user(self, actor: User, *, email: str, password: str, full_name: str | None, role: str, organization_id: uuid.UUID | None = None, department_id: uuid.UUID | None = None) -> User:
        self.permissions.require_permission(actor, "user.manage")
        if role not in USER_ROLES:
            raise ValidationError(f"非法角色:{role}")
        email = email.strip().lower()
        if self.db.scalar(select(User).where(User.email == email)):
            raise ConflictError("该邮箱已存在")
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
            organization_id=organization_id,
            department_id=department_id,
        )
        self.db.add(user)
        self.db.flush()
        self.db.add(UserProfile(user_id=user.id, full_name=full_name))
        self.audit.log(
            "user.create", user_id=actor.id, entity_type="user", entity_id=user.id,
            details={"email": email, "role": role},
        )
        self.db.commit()
        return user

    def update_user(self, actor: User, user_id: uuid.UUID | str, *, role: str | None = None, is_active: bool | None = None, organization_id: uuid.UUID | str | None = None, department_id: uuid.UUID | str | None = None, full_name: str | None = None) -> User:
        self.permissions.require_permission(actor, "user.manage")
        user = self.db.get(User, uuid.UUID(str(user_id)))
        if user is None or user.deleted_at is not None:
            raise NotFoundError("用户不存在")
        if role is not None:
            if role not in USER_ROLES:
                raise ValidationError(f"非法角色:{role}")
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        if organization_id is not None:
            user.organization_id = uuid.UUID(str(organization_id))
        if department_id is not None:
            user.department_id = uuid.UUID(str(department_id))
        if full_name is not None:
            if user.profile is None:
                self.db.add(UserProfile(user_id=user.id, full_name=full_name))
            else:
                user.profile.full_name = full_name
        self.audit.log(
            "user.update", user_id=actor.id, entity_type="user", entity_id=user.id,
            details={"role": role, "is_active": is_active},
        )
        self.db.commit()
        return user

    # ---- organizations / departments ----------------------------------------

    def list_organizations(self) -> list[Organization]:
        return list(
            self.db.scalars(
                select(Organization).where(Organization.deleted_at.is_(None)).order_by(Organization.created_at)
            ).all()
        )

    def create_organization(self, actor: User, *, name: str, code: str, description: str | None = None) -> Organization:
        self.permissions.require_permission(actor, "org.manage")
        code = code.strip().upper()
        if self.db.scalar(select(Organization).where(Organization.code == code)):
            raise ConflictError("组织编码已存在")
        org = Organization(name=name.strip(), code=code, description=description)
        self.db.add(org)
        self.audit.log(
            "organization.create", user_id=actor.id, entity_type="organization", entity_id=org.id,
            details={"name": name, "code": code},
        )
        self.db.commit()
        return org

    def list_departments(self, organization_id: uuid.UUID | None = None) -> list[Department]:
        stmt = select(Department).where(Department.deleted_at.is_(None))
        if organization_id:
            stmt = stmt.where(Department.organization_id == uuid.UUID(str(organization_id)))
        return list(self.db.scalars(stmt.order_by(Department.name)).all())

    def create_department(self, actor: User, *, organization_id: uuid.UUID, name: str) -> Department:
        self.permissions.require_permission(actor, "org.manage")
        dept = Department(organization_id=uuid.UUID(str(organization_id)), name=name.strip())
        self.db.add(dept)
        self.audit.log(
            "department.create", user_id=actor.id, entity_type="department", entity_id=dept.id,
            details={"name": name},
        )
        self.db.commit()
        return dept

    # ---- audit logs ---------------------------------------------------------

    def list_audit_logs(self, *, page: int = 1, page_size: int = 50) -> tuple[list, int]:
        from sqlalchemy import func

        from app.models.audit import AuditLog

        total = int(self.db.scalar(select(func.count(AuditLog.id))) or 0)
        items = list(
            self.db.scalars(
                select(AuditLog)
                .order_by(AuditLog.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return items, total
