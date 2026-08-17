"""FastAPI 依赖：数据库会话、当前用户解析、角色校验。"""

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import forbidden, unauthorized
from app.core.security import decode_token
from app.db import SessionLocal
from app.models.user import User
from app.repositories.user_repository import UserRepository

_bearer = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise unauthorized("缺少访问令牌")
    user_id = decode_token(credentials.credentials, "access")
    if user_id is None:
        raise unauthorized("访问令牌无效或已过期")
    user = UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise unauthorized("访问令牌无效或已过期")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    """角色校验依赖工厂：``Depends(require_roles("admin", "supervisor"))``。"""

    def checker(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise forbidden("当前角色无权执行此操作")
        return current_user

    return checker


def require_permission(code: str):
    """权限码校验依赖工厂（M6）：按当前用户角色查 role_permissions 生效矩阵。"""

    def checker(session: DbSession, current_user: CurrentUser) -> User:
        from app.services.permission_service import PermissionService

        if not PermissionService(session).has_permission(current_user.role, code):
            raise forbidden("当前角色无权执行此操作")
        return current_user

    return checker


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)
