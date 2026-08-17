"""organizations / departments / 权限矩阵的数据访问。业务规则不得出现在此层。"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.organization import Department, Organization, Permission, RolePermission


class OrganizationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self, page: int, page_size: int
    ) -> tuple[list[Organization], int]:
        stmt = select(Organization).where(Organization.deleted_at.is_(None))
        total = self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                stmt.order_by(Organization.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        stmt = select(Organization).where(
            Organization.id == organization_id, Organization.deleted_at.is_(None)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def code_exists(self, code: str, exclude_id: uuid.UUID | None = None) -> bool:
        """code 全局唯一（含已软删除组织，避免唯一索引冲突）。"""
        stmt = select(func.count()).select_from(Organization).where(
            Organization.code == code
        )
        if exclude_id is not None:
            stmt = stmt.where(Organization.id != exclude_id)
        return self.session.execute(stmt).scalar_one() > 0

    def add(self, organization: Organization) -> Organization:
        self.session.add(organization)
        self.session.flush()
        return organization


class DepartmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self, organization_id: uuid.UUID | None, page: int, page_size: int
    ) -> tuple[list[Department], int]:
        stmt = select(Department).where(Department.deleted_at.is_(None))
        if organization_id is not None:
            stmt = stmt.where(Department.organization_id == organization_id)
        total = self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                stmt.order_by(Department.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def get_by_id(self, department_id: uuid.UUID) -> Department | None:
        stmt = select(Department).where(
            Department.id == department_id, Department.deleted_at.is_(None)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def add(self, department: Department) -> Department:
        self.session.add(department)
        self.session.flush()
        return department


class PermissionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_permissions(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.code)
        return list(self.session.execute(stmt).scalars().all())

    def known_codes(self) -> set[str]:
        return set(self.session.execute(select(Permission.code)).scalars().all())

    def replace_role_codes(self, role: str, codes: list[str]) -> None:
        """整体替换某角色的权限码集合。"""
        self.session.execute(
            RolePermission.__table__.delete().where(RolePermission.role == role)
        )
        for code in dict.fromkeys(codes):
            self.session.add(RolePermission(role=role, permission_code=code))
        self.session.flush()
