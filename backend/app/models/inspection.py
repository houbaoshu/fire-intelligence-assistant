"""inspection_records and inspection_record_items tables."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class InspectionRecord(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "inspection_records"
    __table_args__ = (
        Index("ix_inspection_records_created_by", "created_by"),
        Index("ix_inspection_records_status", "status"),
        Index("ix_inspection_records_inspection_date", "inspection_date"),
    )

    record_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inspection_unit: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inspection_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inspection_date: Mapped[datetime | None] = mapped_column(nullable=True)
    inspector_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    items: Mapped[list["InspectionRecordItem"]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
        order_by="InspectionRecordItem.sort_order",
    )


class InspectionRecordItem(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "inspection_record_items"

    inspection_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inspection_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    correction_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    record: Mapped[InspectionRecord] = relationship(back_populates="items")
