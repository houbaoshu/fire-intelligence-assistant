"""FastAPI dependencies: auth, roles, db, storage."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.models.user import User
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("缺少认证凭证")
    return AuthService(db).authenticate_by_token(credentials.credentials)


def require_roles(*roles: str):
    """Dependency factory: require the current user to hold one of the roles."""

    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles and user.role != "admin":
            raise ForbiddenError("权限不足")
        return user

    return checker


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]
