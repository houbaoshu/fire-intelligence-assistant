"""Inspection record application service.

Coordinates: upload -> task creation -> (worker pipeline) -> structured record
-> user review/edit -> finalize -> document generation -> download.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models.enums import RECORD_STATUSES
from app.models.inspection import InspectionRecord, InspectionRecordItem
from app.schemas.inspection_record import InspectionRecordUpdate
from app.services.audit_service import AuditService
from app.services.file_service import FileService
from app.services.tasks.task_service import TaskService

logger = get_logger("inspection")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InspectionRecordService:
    def __init__(self, db: Session):
        self.db = db
        self.files = FileService(db)
        self.tasks = TaskService(db)
        self.audit = AuditService(db)

    # ---- generation ---------------------------------------------------------

    def start_generation(self, user, video: UploadFile, remarks: str | None, idempotency_key: str | None = None) -> uuid.UUID:
        if idempotency_key:
            existing = self.tasks.find_by_idempotency_key(user.id, idempotency_key, "inspection_record_generation")
            if existing is not None:
                return existing.id
        uploaded = self.files.store_upload(video, "video", user.id)
        record = InspectionRecord(
            status="processing",
            created_by=user.id,
            title=remarks or "检查记录",
        )
        self.db.add(record)
        self.db.flush()
        task = self.tasks.create_task(
            "inspection_record_generation",
            user.id,
            input_data={
                "record_id": str(record.id),
                "uploaded_file_id": str(uploaded.id),
                "remarks": remarks or "",
            },
            idempotency_key=idempotency_key,
        )
        self.db.commit()
        self.audit.log(
            "inspection_record.create", user_id=user.id,
            entity_type="inspection_record", entity_id=record.id,
        )
        self.db.commit()
        return task.id

    # ---- queries ------------------------------------------------------------

    def _get_record(self, record_id: uuid.UUID | str) -> InspectionRecord:
        record = self.db.get(InspectionRecord, uuid.UUID(str(record_id)))
        if record is None or record.deleted_at is not None:
            raise NotFoundError("检查记录不存在")
        return record

    def _check_view_permission(self, user, record: InspectionRecord) -> None:
        if user.role in ("admin", "supervisor"):
            return
        if record.created_by != user.id:
            raise ForbiddenError("无权访问该记录")

    def _check_edit_permission(self, user, record: InspectionRecord) -> None:
        if user.role in ("admin", "supervisor"):
            return
        if record.created_by != user.id:
            raise ForbiddenError("无权编辑该记录")

    def get(self, user, record_id: uuid.UUID | str) -> InspectionRecord:
        record = self._get_record(record_id)
        self._check_view_permission(user, record)
        return record

    def list(self, user, *, page: int = 1, page_size: int = 20, status: str | None = None) -> tuple[list[InspectionRecord], int]:
        from sqlalchemy import func

        base = select(InspectionRecord).where(InspectionRecord.deleted_at.is_(None))
        count_base = select(func.count(InspectionRecord.id)).where(InspectionRecord.deleted_at.is_(None))
        if user.role not in ("admin", "supervisor"):
            base = base.where(InspectionRecord.created_by == user.id)
            count_base = count_base.where(InspectionRecord.created_by == user.id)
        if status:
            base = base.where(InspectionRecord.status == status)
            count_base = count_base.where(InspectionRecord.status == status)
        total = int(self.db.scalar(count_base) or 0)
        items = list(
            self.db.scalars(
                base.order_by(InspectionRecord.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return items, total

    # ---- update -------------------------------------------------------------

    def update(self, user, record_id: uuid.UUID | str, payload: InspectionRecordUpdate) -> InspectionRecord:
        record = self._get_record(record_id)
        self._check_edit_permission(user, record)

        if record.status == "finalized":
            # no silent overwrite of finalized content
            has_content_change = any(
                field is not None
                for field in [
                    payload.title,
                    payload.inspection_unit,
                    payload.inspection_address,
                    payload.inspection_date,
                    payload.inspector_names,
                    payload.contact_person,
                    payload.contact_phone,
                    payload.summary,
                    payload.conclusion,
                    payload.items,
                ]
            )
            if has_content_change:
                raise ConflictError("记录已定稿,不能直接修改内容;如需修订请走重新生成流程")
            if payload.status not in (None, "archived"):
                raise ConflictError("记录已定稿,仅允许归档操作")

        data = payload.model_dump(exclude_unset=True)
        items_payload = data.pop("items", None)
        new_status = data.pop("status", None)

        for field, value in data.items():
            setattr(record, field, value)

        if items_payload is not None:
            self._replace_items(record, items_payload)

        if new_status is not None:
            if new_status not in RECORD_STATUSES:
                raise ConflictError(f"非法状态:{new_status}")
            record.status = new_status
            if new_status == "finalized":
                self._finalize(record, user)

        self.audit.log(
            "inspection_record.update", user_id=user.id,
            entity_type="inspection_record", entity_id=record.id,
        )
        self.db.commit()
        self.db.refresh(record)
        return record

    def _replace_items(self, record: InspectionRecord, items: list[dict]) -> None:
        existing = {str(item.id): item for item in record.items}
        seen: set[str] = set()
        for order, item_data in enumerate(items):
            item_id = item_data.get("id")
            item_data["sort_order"] = order
            if item_id:
                if item_id in seen:
                    raise ConflictError("检查项 id 重复")
                seen.add(item_id)
                item = existing.get(item_id)
                if item is None:
                    raise ConflictError("检查项不属于该记录")
                for k, v in item_data.items():
                    if k != "id":
                        setattr(item, k, v)
            else:
                item = InspectionRecordItem(
                    inspection_record_id=record.id,
                    item_type=item_data.get("item_type", "observation"),
                    location=item_data.get("location"),
                    description=item_data.get("description", ""),
                    legal_basis=item_data.get("legal_basis"),
                    correction_requirement=item_data.get("correction_requirement"),
                    severity=item_data.get("severity"),
                    sort_order=order,
                )
                self.db.add(item)
        # delete items not present anymore
        for item_id, item in existing.items():
            if item_id not in seen:
                self.db.delete(item)

    def _finalize(self, record: InspectionRecord, user) -> None:
        """Mark finalized, assign record number, enqueue document generation."""
        if not record.record_number:
            record.record_number = self._next_record_number()
        record.status = "finalized"
        self.audit.log(
            "inspection_record.finalize", user_id=user.id,
            entity_type="inspection_record", entity_id=record.id,
        )
        task = self.tasks.create_task(
            "document_generation",
            user.id,
            input_data={
                "entity_type": "inspection_record",
                "entity_id": str(record.id),
            },
        )
        self.db.flush()

    def _next_record_number(self) -> str:
        year = _utcnow().year
        prefix = f"JC-{year}-"
        stmt = select(InspectionRecord.record_number).where(
            InspectionRecord.record_number.like(f"{prefix}%")
        )
        existing = [
            int(r.split("-")[-1])
            for r in self.db.scalars(stmt).all()
            if r and r.split("-")[-1].isdigit()
        ]
        seq = (max(existing) + 1) if existing else 1
        return f"{prefix}{seq:04d}"

    # ---- document download --------------------------------------------------

    def download(self, user, record_id: uuid.UUID | str) -> tuple[bytes, str]:
        from app.services.document_service import DocumentService

        record = self._get_record(record_id)
        self._check_view_permission(user, record)
        return DocumentService(self.db).download_latest(
            user, entity_type="inspection_record", entity_id=record.id,
            fallback_filename=f"inspection-record-{record.record_number or record.id}.docx",
        )
