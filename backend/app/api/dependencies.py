"""FastAPI dependency functions for authentication and authorization."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import verify_token


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: AsyncSession = Depends(get_db),
):
    """Extract and validate the Bearer token, returning the current user.

    Raises ``UnauthorizedException`` when the token is missing, invalid,
    or the referenced user does not exist.
    """
    if not authorization:
        raise UnauthorizedException("Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException(
            "Invalid Authorization header format; expected 'Bearer <token>'"
        )

    try:
        payload = verify_token(token)
    except JWTError as exc:
        raise UnauthorizedException(f"Invalid or expired token: {exc}") from exc

    # Reject refresh tokens presented as access tokens.
    if payload.get("type") == "refresh":
        raise UnauthorizedException("Refresh tokens cannot be used for API access")

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise UnauthorizedException("Token payload missing 'sub' claim")

    # Import here to avoid circular imports at module level.
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise UnauthorizedException("User account is disabled")

    return user


def require_role(*roles: str) -> Callable:
    """Return a dependency that ensures the current user has one of the
    specified *roles*.

    Usage::

        @router.get("/admin-only")
        async def admin_endpoint(user=Depends(require_role("admin"))):
            ...
    """

    async def _checker(
        current_user=Depends(get_current_user),
    ):
        if current_user.role not in roles:
            raise ForbiddenException(
                f"Role '{current_user.role}' is not authorized; required one of: {', '.join(roles)}"
            )
        return current_user

    return _checker
