"""Organization, Department, and UserRole ORM models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Organization(Base):
    """An enterprise / organization entity."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    departments: Mapped[list[Department]] = relationship(
        back_populates="organization", lazy="noload"
    )
    user_roles: Mapped[list[UserRole]] = relationship(back_populates="organization", lazy="noload")

    def __repr__(self) -> str:
        return f"<Organization id={self.id} name={self.name!r}>"


class Department(Base):
    """A department within an organization, supporting nested hierarchy."""

    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    organization: Mapped[Organization] = relationship(back_populates="departments")
    children: Mapped[list[Department]] = relationship(back_populates="parent", lazy="noload")
    parent: Mapped[Department | None] = relationship(
        back_populates="children", remote_side=[id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Department id={self.id} name={self.name!r}>"


class UserRole(Base):
    """Many-to-many association between users and custom roles within an organization."""

    __tablename__ = "user_roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_name: Mapped[str] = mapped_column(String(50), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    organization: Mapped[Organization | None] = relationship(back_populates="user_roles")

    def __repr__(self) -> str:
        return f"<UserRole id={self.id} user_id={self.user_id} role={self.role_name!r}>"
