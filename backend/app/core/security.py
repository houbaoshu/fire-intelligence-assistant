"""Security helpers: JWT tokens and password hashing."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from .config import get_settings
from .exceptions import UnauthorizedError

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (salt embedded). Never store plaintext."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _secret() -> str:
    return get_settings().SECRET_KEY


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = _utcnow()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(
        user_id,
        "access",
        timedelta(minutes=get_settings().ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        user_id,
        "refresh",
        timedelta(days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: str) -> str:
    """Decode and validate a JWT. Returns the user id (subject)."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("会话已过期,请重新登录") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedError("无效的会话凭证") from None
    if payload.get("type") != expected_type:
        raise UnauthorizedError("无效的会话凭证")
    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("无效的会话凭证")
    return sub
