"""users and user_profiles tables (see DATABASE.md)."""
from __future__ import annotations

import uuid
from datetime import datetime

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class User(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="inspector")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def to_public_dict(self) -> dict:
        full_name = self.profile.full_name if self.profile else None
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": full_name,
            "role": self.role,
        }


class UserProfile(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"
    __table_args__ = (Index("uq_user_profiles_user_id", "user_id", unique=True),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")
