"""User ORM model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """Application user (inspection officers, admins, etc.)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    auth_provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="inspector")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    profile: Mapped[UserProfile | None] = relationship(  # noqa: F821
        back_populates="user", uselist=False, lazy="selectin"
    )
    inspection_records: Mapped[list[InspectionRecord]] = relationship(  # noqa: F821
        back_populates="creator", lazy="noload"
    )
    ai_tasks: Mapped[list[AITask]] = relationship(  # noqa: F821
        back_populates="creator", lazy="noload"
    )
    interview_records: Mapped[list[InterviewRecord]] = relationship(  # noqa: F821
        back_populates="creator", lazy="noload"
    )
    photo_reports: Mapped[list[PhotoReport]] = relationship(  # noqa: F821
        back_populates="creator", lazy="noload"
    )
    knowledge_documents: Mapped[list[KnowledgeDocument]] = relationship(  # noqa: F821
        back_populates="creator", lazy="noload"
    )
    generated_documents: Mapped[list[GeneratedDocument]] = relationship(  # noqa: F821
        back_populates="creator", lazy="noload"
    )
    uploaded_files: Mapped[list[UploadedFile]] = relationship(  # noqa: F821
        back_populates="uploader", lazy="noload"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(  # noqa: F821
        back_populates="user", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
