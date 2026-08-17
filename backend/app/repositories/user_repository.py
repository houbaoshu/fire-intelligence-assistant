"""用户与审计日志的数据库访问。业务规则不得出现在此层。"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

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


class AuditLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, entry: AuditLog) -> AuditLog:
        """审计日志只追加，不提供更新/删除。"""
        self.session.add(entry)
        self.session.flush()
        return entry
