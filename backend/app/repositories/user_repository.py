"""用户与审计日志的数据库访问。业务规则不得出现在此层。"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.user import AuditLog, User, UserProfile, utc_now


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user

    def touch_last_login(self, user: User) -> None:
        user.last_login_at = utc_now()
        self.session.flush()

    def list_admin(
        self,
        organization_id: uuid.UUID | None,
        role: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[User], int]:
        stmt = (
            select(User)
            .options(joinedload(User.profile))
            .where(User.deleted_at.is_(None))
        )
        if organization_id is not None:
            stmt = stmt.where(User.organization_id == organization_id)
        if role is not None:
            stmt = stmt.where(User.role == role)
        total = self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                stmt.order_by(User.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .unique()
            .all()
        )
        return list(rows), total

    def count_by_organization(self, organization_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(User).where(
            User.organization_id == organization_id, User.deleted_at.is_(None)
        )
        return self.session.execute(stmt).scalar_one()

    def count_by_department(self, department_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(User).where(
            User.department_id == department_id, User.deleted_at.is_(None)
        )
        return self.session.execute(stmt).scalar_one()

    def ids_in_organization(self, organization_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(User.id).where(
            User.organization_id == organization_id, User.deleted_at.is_(None)
        )
        return list(self.session.execute(stmt).scalars().all())


class AuditLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, entry: AuditLog) -> AuditLog:
        """审计日志只追加，不提供更新/删除。"""
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_admin(
        self,
        user_id: uuid.UUID | None,
        action: str | None,
        entity_type: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if entity_type is not None:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        total = self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                stmt.order_by(AuditLog.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), total
