"""inspection_records / inspection_record_items 模型，列定义以 DATABASE.md 为准。"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONVariant, UTCDateTime, new_uuid, utc_now

# 三组业务记录共享同一状态机（DATABASE.md）
RECORD_STATUSES = (
    "draft",
    "processing",
    "generated",
    "reviewed",
    "finalized",
    "archived",
    "failed",
)

ITEM_TYPES = ("compliant", "violation", "hazard", "observation", "recommendation")
SEVERITIES = ("low", "medium", "high", "critical")


def _in_clause(values: tuple[str, ...]) -> str:
    return ", ".join(repr(v) for v in values)


class InspectionRecord(Base):
    __tablename__ = "inspection_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    record_number: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    inspection_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    inspection_address: Mapped[str | None] = mapped_column(String, nullable=True)
    inspection_date: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    inspector_names: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_tasks.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    items: Mapped[list["InspectionRecordItem"]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
        order_by="InspectionRecordItem.sort_order",
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({_in_clause(RECORD_STATUSES)})", name="ck_inspection_records_status"
        ),
        Index("ix_inspection_records_created_by", "created_by"),
        Index("ix_inspection_records_status", "status"),
        Index("ix_inspection_records_inspection_date", "inspection_date"),
        Index(
            "ix_inspection_records_created_by_status_created_at",
            "created_by",
            "status",
            "created_at",
        ),
    )


class InspectionRecordItem(Base):
    __tablename__ = "inspection_record_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    inspection_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inspection_records.id"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    correction_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    record: Mapped[InspectionRecord] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint(
            f"item_type IN ({_in_clause(ITEM_TYPES)})",
            name="ck_inspection_record_items_item_type",
        ),
        CheckConstraint(
            f"severity IN ({_in_clause(SEVERITIES)})",
            name="ck_inspection_record_items_severity",
        ),
    )
