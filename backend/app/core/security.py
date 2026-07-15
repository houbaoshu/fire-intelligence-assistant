"""Security utilities: password hashing and JWT token management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# ── Password hashing ────────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` if *plain_password* matches *hashed_password*."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT tokens ──────────────────────────────────────────────────────────────


def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    """Encode a JWT with the given *data* and *expires_delta*."""
    settings = get_settings()
    now = datetime.now(UTC)
    to_encode = data.copy()
    to_encode.update({"exp": now + expires_delta, "iat": now})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived access token.

    Parameters
    ----------
    data:
        Claims to include (must contain ``sub``).
    expires_delta:
        Optional custom expiry; defaults to
        ``settings.access_token_expire_minutes``.
    """
    settings = get_settings()
    delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    return _create_token(data, delta)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a long-lived refresh token.

    The token includes a ``type`` claim set to ``"refresh"`` so it can
    be distinguished from access tokens during verification.
    """
    settings = get_settings()
    payload = {**data, "type": "refresh"}
    delta = timedelta(days=settings.refresh_token_expire_days)
    return _create_token(payload, delta)


def verify_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT, returning its payload.

    Raises
    ------
    jose.JWTError
        If the token is expired, malformed, or has an invalid signature.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise
    return payload
