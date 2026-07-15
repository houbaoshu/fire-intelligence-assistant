from __future__ import annotations

from typing import cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.security import TokenError, decode_token
from app.db.models import User
from app.db.session import get_db
from app.repositories.users import UserRepository

bearer = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_signing_key(request: Request) -> bytes:
    return cast(bytes, request.app.state.signing_key)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            status_code=401,
            code="AUTHENTICATION_REQUIRED",
            message="Authentication is required.",
        )
    try:
        payload = decode_token(
            credentials.credentials,
            expected_type="access",
            secret=request.app.state.signing_key,
        )
    except TokenError as error:
        raise AppError(
            status_code=401,
            code="INVALID_TOKEN",
            message="The session is invalid or has expired.",
        ) from error
    user = UserRepository(session).get_by_id(payload.subject)
    if user is None or not user.is_active:
        raise AppError(
            status_code=401,
            code="INVALID_TOKEN",
            message="The session is invalid or has expired.",
        )
    return user
