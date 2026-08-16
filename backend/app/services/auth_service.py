"""Authentication & user management service."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import USER_ROLES
from app.models.user import User, UserProfile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    # ---- registration / login ------------------------------------------------

    def register(self, email: str, password: str, full_name: str | None) -> User:
        settings = get_settings()
        if not settings.REGISTRATION_ENABLED:
            raise ForbiddenError("注册功能未开放")
        email = email.strip().lower()
        existing = self.db.scalar(select(User).where(User.email == email))
        if existing:
            raise ConflictError("该邮箱已注册")
        user = User(
            email=email,
            password_hash=hash_password(password),
            username=None,
            role="inspector",  # ordinary registration can never choose a privileged role
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        self.db.add(UserProfile(user_id=user.id, full_name=full_name))
        self.db.flush()
        return user

    def login(self, email: str, password: str) -> User:
        email = email.strip().lower()
        user = self.db.scalar(select(User).where(User.email == email))
        if user is None or not verify_password(password, user.password_hash):
            # generic message: no account enumeration
            raise UnauthorizedError("邮箱或密码错误")
        if not user.is_active or user.deleted_at is not None:
            raise ForbiddenError("账号已停用,请联系管理员")
        user.last_login_at = _utcnow()
        return user

    def authenticate_by_token(self, access_token: str) -> User:
        user_id = decode_token(access_token, "access")
        user = self.db.get(User, uuid.UUID(user_id))
        if user is None or not user.is_active or user.deleted_at is not None:
            raise UnauthorizedError("账号不可用,请重新登录")
        return user

    def refresh(self, refresh_token: str) -> str:
        user_id = decode_token(refresh_token, "refresh")
        user = self.db.get(User, uuid.UUID(user_id))
        if user is None or not user.is_active or user.deleted_at is not None:
            raise UnauthorizedError("账号不可用,请重新登录")
        return create_access_token(user_id)

    def issue_tokens(self, user: User) -> dict:
        return {
            "access_token": create_access_token(str(user.id)),
            "refresh_token": create_refresh_token(str(user.id)),
        }

    def require_role(self, user: User, allowed_roles: tuple[str, ...]) -> None:
        """Raise ForbiddenError unless user.role is in allowed_roles.

        Role ordering: viewer < inspector < supervisor < admin.
        """
        if user.role not in USER_ROLES:
            raise ForbiddenError("未知角色")
        if user.role not in allowed_roles:
            # admin can do anything
            if user.role == "admin":
                return
            raise ForbiddenError("权限不足")
