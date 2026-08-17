"""询问记录业务逻辑（API.md §4.3）。router 保持薄，规则收敛于此。"""

import uuid

from app.core.exceptions import AppException
from app.models.ai_task import AITask
from app.models.interview import InterviewRecord
from app.models.user import User
from app.repositories.interview_repository import InterviewRecordRepository
from app.schemas.common import Page
from app.schemas.records import (
    InterviewRecordDetail,
    InterviewRecordListItem,
    InterviewRecordUpdate,
)
from app.services.documents import DocumentGenerationService
from app.services.records_base import RecordServiceBase


class InterviewRecordService(RecordServiceBase):
    audit_entity = "interview_record"
    record_kind = "interview_record"

    def __init__(self, session, storage=None) -> None:
        super().__init__(session, storage)
        self.records = InterviewRecordRepository(session)

    def generate(
        self,
        *,
        user: User,
        filename: str | None,
        content_type: str | None,
        data: bytes,
        remarks: str | None,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> AITask:
        record = InterviewRecord(status="processing", created_by=user.id)
        return self._start_generation(
            user=user,
            filename=filename,
            content_type=content_type,
            data=data,
            category="audio",
            task_type="interview_record_generation",
            record=record,
            remarks=remarks,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def list(
        self, user: User, status: str | None, page: int, page_size: int
    ) -> Page[InterviewRecordListItem]:
        rows, total = self.records.list_scoped(
            self._visible_creator_ids(user), status, page, page_size
        )
        return Page(
            items=[self._to_list_item(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def detail(self, user: User, record_id: uuid.UUID) -> InterviewRecordDetail:
        record = self._get_or_404(self.records, record_id, user, "询问记录")
        return self._to_detail(record)

    def update(
        self,
        user: User,
        record_id: uuid.UUID,
        payload: InterviewRecordUpdate,
        request_id: str | None = None,
    ) -> InterviewRecordDetail:
        record = self._get_or_404(self.records, record_id, user, "询问记录")
        self._guard_not_finalized(record)
        self._check_update_permission(
            user, record, payload.status if "status" in payload.model_fields_set else None
        )

        data = payload.model_dump(exclude_unset=True)
        new_status = data.pop("status", None)
        for field_name, value in data.items():
            setattr(record, field_name, value)

        # 业务规则：started_at 不得晚于 ended_at（specs/interview-record.md）
        if (
            record.started_at is not None
            and record.ended_at is not None
            and record.started_at > record.ended_at
        ):
            raise AppException(
                "VALIDATION_ERROR", "开始时间不得晚于结束时间", 400
            )

        became_finalized = new_status == "finalized" and record.status != "finalized"
        if new_status is not None:
            record.status = new_status
        if became_finalized:
            self._audit_finalize(user, record, request_id)
        self.session.commit()
        self.session.refresh(record)
        return self._to_detail(record)

    def download(
        self, user: User, record_id: uuid.UUID, request_id: str | None = None
    ) -> tuple[str, bytes]:
        record = self._get_or_404(self.records, record_id, user, "询问记录")
        filename, data, document = DocumentGenerationService(
            self.session, self.files.storage
        ).generate(
            entity_type="interview_record",
            entity=record,
            created_by=user.id,
            task_id=record.source_task_id,
        )
        self._audit_download(user, record, document.id, request_id)
        self.session.commit()
        return filename, data

    # ---------- 内部 ----------

    @staticmethod
    def _to_list_item(record: InterviewRecord) -> InterviewRecordListItem:
        return InterviewRecordListItem(
            id=record.id,
            title=record.title,
            interviewee_name=record.interviewee_name,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _to_detail(record: InterviewRecord) -> InterviewRecordDetail:
        return InterviewRecordDetail(
            id=record.id,
            title=record.title,
            interviewee_name=record.interviewee_name,
            interviewer_names=record.interviewer_names,
            location=record.location,
            started_at=record.started_at,
            ended_at=record.ended_at,
            transcript=record.transcript,
            structured_content=record.structured_content,
            status=record.status,
            source_task_id=record.source_task_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
