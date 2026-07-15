"""Repository for User database operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Encapsulates all database access for :class:`User`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        """Return a single user by primary key, or *None* if not found."""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by email address, excluding soft-deleted."""
        stmt = select(User).where(
            User.email == email,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        hashed_password: str,
        username: str | None = None,
        role: str = "inspector",
    ) -> User:
        """Create and persist a new user, then return the flushed instance."""
        user = User(
            email=email,
            hashed_password=hashed_password,
            username=username or email.split("@")[0],
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_last_login(self, user_id: str) -> None:
        """Update the last_login_at timestamp."""
        now = datetime.now(UTC)
        stmt = update(User).where(User.id == user_id).values(last_login_at=now, updated_at=now)
        await self.db.execute(stmt)
        await self.db.flush()

    async def list_active(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Return a paginated list of active (non-deleted) users."""
        stmt = (
            select(User)
            .where(User.is_active.is_(True), User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
