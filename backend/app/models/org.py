"""organizations and departments tables (Milestone 6)."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class Organization(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class Department(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (Index("ix_departments_organization_id", "organization_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
