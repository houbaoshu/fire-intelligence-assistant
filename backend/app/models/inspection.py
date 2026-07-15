"""InspectionRecord and InspectionRecordItem models."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class InspectionRecord(Base):
    __tablename__ = "inspection_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    record_number: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    inspection_unit: Mapped[str | None] = mapped_column(String(500), nullable=True)
    inspection_address: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    inspection_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inspector_names: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True
    )  # draft / processing / generated / reviewed / finalized / archived / failed
    source_task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ai_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────
    creator: Mapped["User"] = relationship(  # noqa: F821
        back_populates="inspection_records"
    )
    source_task: Mapped["AITask | None"] = relationship(  # noqa: F821
        back_populates="inspection_records", foreign_keys=[source_task_id]
    )
    items: Mapped[list["InspectionRecordItem"]] = relationship(
        back_populates="inspection_record",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        # Composite index for common listing queries
    )

    def __repr__(self) -> str:
        return (
            f"<InspectionRecord id={self.id} record_number={self.record_number!r} "
            f"status={self.status!r}>"
        )


class InspectionRecordItem(Base):
    __tablename__ = "inspection_record_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inspection_record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("inspection_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # compliant / violation / hazard / observation / recommendation
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    correction_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # low / medium / high / critical
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    # ── Relationships ─────────────────────────────────────────
    inspection_record: Mapped["InspectionRecord"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return (
            f"<InspectionRecordItem id={self.id} item_type={self.item_type!r} "
            f"severity={self.severity!r}>"
        )
