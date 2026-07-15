"""Authentication service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User

logger = get_logger(__name__)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session.

        Args:
            db: Async database session.
        """
        self.db = db

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        """Validate credentials and return user with tokens.

        Args:
            email: User email address.
            password: Plain text password.

        Returns:
            Tuple of (user, access_token, refresh_token).

        Raises:
            UnauthorizedException: If credentials are invalid.
        """
        logger.info("Login attempt", extra={"email": email})

        # Find user by email
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedException("User account is disabled")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")

        # Create tokens
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        logger.info("Login successful", extra={"user_id": str(user.id)})

        return user, access_token, refresh_token

    async def register(
        self,
        email: str,
        password: str,
        username: str | None = None,
    ) -> tuple[User, str, str]:
        """Create a new user account.

        Args:
            email: User email address.
            password: Plain text password.
            username: Optional display username.

        Returns:
            Tuple of (user, access_token, refresh_token).

        Raises:
            ConflictException: If email already exists.
        """
        logger.info("Registration attempt", extra={"email": email})

        # Check for existing email
        result = await self.db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ConflictException("Email already registered")

        # Create user
        user = User(
            email=email,
            username=username or email.split("@")[0],
            hashed_password=hash_password(password),
            role="officer",
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()

        # Create tokens
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        logger.info("Registration successful", extra={"user_id": str(user.id)})

        return user, access_token, refresh_token
