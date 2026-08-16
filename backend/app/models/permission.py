"""permissions and role_permissions tables (fine-grained authorization)."""
from __future__ import annotations

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPkMixin


class Permission(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class RolePermission(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role", "permission_code", name="uq_role_permission"),
    )

    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    permission_code: Mapped[str] = mapped_column(String(100), nullable=False)
