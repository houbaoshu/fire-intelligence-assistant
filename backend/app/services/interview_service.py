"""Interview record application service (v1: audio source only)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.enums import RECORD_STATUSES
from app.models.interview import InterviewRecord
from app.schemas.interview_record import InterviewRecordUpdate
from app.services.audit_service import AuditService
from app.services.file_service import FileService
from app.services.tasks.task_service import TaskService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InterviewRecordService:
    def __init__(self, db: Session):
        self.db = db
        self.files = FileService(db)
        self.tasks = TaskService(db)
        self.audit = AuditService(db)

    def start_generation(self, user, audio: UploadFile, remarks: str | None, idempotency_key: str | None = None) -> uuid.UUID:
        if idempotency_key:
            existing = self.tasks.find_by_idempotency_key(user.id, idempotency_key, "interview_record_generation")
            if existing is not None:
                return existing.id
        uploaded = self.files.store_upload(audio, "audio", user.id)
        record = InterviewRecord(status="processing", created_by=user.id, title=remarks or "询问记录")
        self.db.add(record)
        self.db.flush()
        task = self.tasks.create_task(
            "interview_record_generation",
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
            "interview_record.create", user_id=user.id,
            entity_type="interview_record", entity_id=record.id,
        )
        self.db.commit()
        return task.id

    def _get_record(self, record_id: uuid.UUID | str) -> InterviewRecord:
        record = self.db.get(InterviewRecord, uuid.UUID(str(record_id)))
        if record is None or record.deleted_at is not None:
            raise NotFoundError("询问记录不存在")
        return record

    def _check_view(self, user, record: InterviewRecord) -> None:
        if user.role in ("admin", "supervisor"):
            return
        if record.created_by != user.id:
            raise ForbiddenError("无权访问该记录")

    def _check_edit(self, user, record: InterviewRecord) -> None:
        if user.role in ("admin", "supervisor"):
            return
        if record.created_by != user.id:
            raise ForbiddenError("无权编辑该记录")

    def get(self, user, record_id: uuid.UUID | str) -> InterviewRecord:
        record = self._get_record(record_id)
        self._check_view(user, record)
        return record

    def list(self, user, *, page: int = 1, page_size: int = 20, status: str | None = None) -> tuple[list[InterviewRecord], int]:
        from sqlalchemy import func

        base = select(InterviewRecord).where(InterviewRecord.deleted_at.is_(None))
        count_base = select(func.count(InterviewRecord.id)).where(InterviewRecord.deleted_at.is_(None))
        if user.role not in ("admin", "supervisor"):
            base = base.where(InterviewRecord.created_by == user.id)
            count_base = count_base.where(InterviewRecord.created_by == user.id)
        if status:
            base = base.where(InterviewRecord.status == status)
            count_base = count_base.where(InterviewRecord.status == status)
        total = int(self.db.scalar(count_base) or 0)
        items = list(
            self.db.scalars(
                base.order_by(InterviewRecord.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return items, total

    def update(self, user, record_id: uuid.UUID | str, payload: InterviewRecordUpdate) -> InterviewRecord:
        record = self._get_record(record_id)
        self._check_edit(user, record)

        if record.status == "finalized":
            content_fields = [
                payload.title, payload.interviewee_name, payload.interviewer_names,
                payload.location, payload.started_at, payload.ended_at,
                payload.transcript, payload.structured_content,
            ]
            if any(f is not None for f in content_fields):
                raise ConflictError("记录已定稿,不能直接修改内容")
            if payload.status not in (None, "archived"):
                raise ConflictError("记录已定稿,仅允许归档操作")

        data = payload.model_dump(exclude_unset=True)
        new_status = data.pop("status", None)
        for field, value in data.items():
            setattr(record, field, value)

        if (
            record.started_at is not None
            and record.ended_at is not None
            and record.started_at > record.ended_at
        ):
            raise ValidationError("开始时间不得晚于结束时间")

        if new_status is not None:
            if new_status not in RECORD_STATUSES:
                raise ConflictError(f"非法状态:{new_status}")
            record.status = new_status
            if new_status == "finalized":
                if not record.transcript or not record.structured_content:
                    raise ValidationError("缺少转写文本或结构化内容,无法定稿")
                self._finalize(record, user)

        self.audit.log(
            "interview_record.update", user_id=user.id,
            entity_type="interview_record", entity_id=record.id,
        )
        self.db.commit()
        self.db.refresh(record)
        return record

    def _finalize(self, record: InterviewRecord, user) -> None:
        record.status = "finalized"
        self.audit.log(
            "interview_record.finalize", user_id=user.id,
            entity_type="interview_record", entity_id=record.id,
        )
        task = self.tasks.create_task(
            "document_generation",
            user.id,
            input_data={"entity_type": "interview_record", "entity_id": str(record.id)},
        )
        self.db.flush()

    def download(self, user, record_id: uuid.UUID | str) -> tuple[bytes, str]:
        from app.services.document_service import DocumentService

        record = self._get_record(record_id)
        self._check_view(user, record)
        return DocumentService(self.db).download_latest(
            user, entity_type="interview_record", entity_id=record.id,
            fallback_filename=f"interview-record-{record.id}.docx",
        )
