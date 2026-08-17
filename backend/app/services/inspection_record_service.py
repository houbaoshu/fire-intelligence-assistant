"""检查记录业务逻辑（API.md §4.1）。router 保持薄，规则收敛于此。"""

import uuid

from app.core.exceptions import AppException
from app.models.ai_task import AITask
from app.models.inspection import InspectionRecord, InspectionRecordItem
from app.models.user import User
from app.repositories.inspection_repository import InspectionRecordRepository
from app.schemas.records import (
    InspectionItemResponse,
    InspectionRecordDetail,
    InspectionRecordListItem,
    InspectionRecordUpdate,
)
from app.services.documents import DocumentGenerationService
from app.services.records_base import RecordServiceBase
from app.schemas.common import Page


class InspectionRecordService(RecordServiceBase):
    audit_entity = "inspection_record"
    record_kind = "inspection_record"

    def __init__(self, session, storage=None) -> None:
        super().__init__(session, storage)
        self.records = InspectionRecordRepository(session)

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
        record = InspectionRecord(status="processing", created_by=user.id)
        return self._start_generation(
            user=user,
            filename=filename,
            content_type=content_type,
            data=data,
            category="video",
            task_type="inspection_record_generation",
            record=record,
            remarks=remarks,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def list(
        self, user: User, status: str | None, page: int, page_size: int
    ) -> Page[InspectionRecordListItem]:
        rows, total = self.records.list_scoped(
            self._visible_creator_ids(user), status, page, page_size
        )
        return Page(
            items=[self._to_list_item(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def detail(self, user: User, record_id: uuid.UUID) -> InspectionRecordDetail:
        record = self._get_or_404(self.records, record_id, user, "检查记录")
        return self._to_detail(record)

    def update(
        self,
        user: User,
        record_id: uuid.UUID,
        payload: InspectionRecordUpdate,
        request_id: str | None = None,
    ) -> InspectionRecordDetail:
        record = self._get_or_404(self.records, record_id, user, "检查记录")
        self._guard_not_finalized(record)
        self._check_update_permission(
            user, record, payload.status if "status" in payload.model_fields_set else None
        )

        data = payload.model_dump(exclude_unset=True)
        new_status = data.pop("status", None)
        items_payload = data.pop("items", None)
        for field_name, value in data.items():
            setattr(record, field_name, value)

        if items_payload is not None:
            self._replace_items(record, payload.items or [])

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
        """按需渲染：以已保存结构化数据生成新版本文书并返回文件流。"""
        record = self._get_or_404(self.records, record_id, user, "检查记录")
        filename, data, document = DocumentGenerationService(
            self.session, self.files.storage
        ).generate(
            entity_type="inspection_record",
            entity=record,
            created_by=user.id,
            task_id=record.source_task_id,
        )
        self._audit_download(user, record, document.id, request_id)
        self.session.commit()
        return filename, data

    # ---------- 内部 ----------

    def _replace_items(self, record: InspectionRecord, items) -> None:
        """items 整体替换：无 id=新增；省略已有 id=删除（cascade delete-orphan）。"""
        existing = {item.id: item for item in record.items}
        replaced: list[InspectionRecordItem] = []
        for item_in in items:
            if item_in.id is not None:
                item = existing.get(item_in.id)
                if item is None:
                    raise AppException("VALIDATION_ERROR", "检查项不属于该记录", 400)
                item.item_type = item_in.item_type
                item.location = item_in.location
                item.description = item_in.description
                item.legal_basis = item_in.legal_basis
                item.correction_requirement = item_in.correction_requirement
                item.severity = item_in.severity
                item.sort_order = item_in.sort_order
            else:
                item = InspectionRecordItem(
                    item_type=item_in.item_type,
                    location=item_in.location,
                    description=item_in.description,
                    legal_basis=item_in.legal_basis,
                    correction_requirement=item_in.correction_requirement,
                    severity=item_in.severity,
                    sort_order=item_in.sort_order,
                )
            replaced.append(item)
        record.items = replaced

    @staticmethod
    def _to_list_item(record: InspectionRecord) -> InspectionRecordListItem:
        return InspectionRecordListItem(
            id=record.id,
            record_number=record.record_number,
            title=record.title,
            inspection_unit=record.inspection_unit,
            inspection_date=record.inspection_date,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _to_detail(record: InspectionRecord) -> InspectionRecordDetail:
        return InspectionRecordDetail(
            id=record.id,
            record_number=record.record_number,
            title=record.title,
            inspection_unit=record.inspection_unit,
            inspection_address=record.inspection_address,
            inspection_date=record.inspection_date,
            inspector_names=record.inspector_names,
            contact_person=record.contact_person,
            contact_phone=record.contact_phone,
            summary=record.summary,
            conclusion=record.conclusion,
            status=record.status,
            items=[
                InspectionItemResponse(
                    id=item.id,
                    item_type=item.item_type,
                    location=item.location,
                    description=item.description,
                    legal_basis=item.legal_basis,
                    correction_requirement=item.correction_requirement,
                    severity=item.severity,
                    sort_order=item.sort_order,
                )
                for item in record.items
            ],
            source_task_id=record.source_task_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
