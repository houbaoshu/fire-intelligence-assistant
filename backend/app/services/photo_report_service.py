"""拍照报告业务逻辑（API.md §4.2）。router 保持薄，规则收敛于此。"""

import uuid

from app.core.exceptions import AppException
from app.models.ai_task import AITask
from app.models.photo_report import PhotoReport
from app.models.user import User
from app.repositories.photo_report_repository import PhotoReportRepository
from app.schemas.common import Page
from app.schemas.records import (
    PhotoReportDetail,
    PhotoReportImageResponse,
    PhotoReportListItem,
    PhotoReportUpdate,
)
from app.services.documents import DocumentGenerationService
from app.services.records_base import RecordServiceBase


class PhotoReportService(RecordServiceBase):
    audit_entity = "photo_report"
    record_kind = "photo_report"

    def __init__(self, session, storage=None) -> None:
        super().__init__(session, storage)
        self.reports = PhotoReportRepository(session)

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
        report = PhotoReport(status="processing", created_by=user.id)
        return self._start_generation(
            user=user,
            filename=filename,
            content_type=content_type,
            data=data,
            category="video",
            task_type="photo_report_generation",
            record=report,
            remarks=remarks,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def list(
        self, user: User, status: str | None, page: int, page_size: int
    ) -> Page[PhotoReportListItem]:
        rows, total = self.reports.list_scoped(
            self._visible_creator_ids(user), status, page, page_size
        )
        return Page(
            items=[self._to_list_item(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def detail(self, user: User, report_id: uuid.UUID) -> PhotoReportDetail:
        report = self._get_or_404(self.reports, report_id, user, "拍照报告")
        return self._to_detail(report)

    def update(
        self,
        user: User,
        report_id: uuid.UUID,
        payload: PhotoReportUpdate,
        request_id: str | None = None,
    ) -> PhotoReportDetail:
        report = self._get_or_404(self.reports, report_id, user, "拍照报告")
        self._guard_not_finalized(report)
        self._check_update_permission(
            user, report, payload.status if "status" in payload.model_fields_set else None
        )

        data = payload.model_dump(exclude_unset=True)
        new_status = data.pop("status", None)
        images_payload = data.pop("images", None)
        for field_name, value in data.items():
            setattr(report, field_name, value)

        if images_payload is not None:
            self._update_images(report, payload.images or [])

        became_finalized = new_status == "finalized" and report.status != "finalized"
        if new_status is not None:
            report.status = new_status
        if became_finalized:
            self._audit_finalize(user, report, request_id)
        self.session.commit()
        self.session.refresh(report)
        return self._to_detail(report)

    def download(
        self, user: User, report_id: uuid.UUID, request_id: str | None = None
    ) -> tuple[str, bytes]:
        report = self._get_or_404(self.reports, report_id, user, "拍照报告")
        filename, data, document = DocumentGenerationService(
            self.session, self.files.storage
        ).generate(
            entity_type="photo_report",
            entity=report,
            created_by=user.id,
            task_id=report.source_task_id,
        )
        self._audit_download(user, report, document.id, request_id)
        self.session.commit()
        return filename, data

    # ---------- 内部 ----------

    @staticmethod
    def _update_images(report: PhotoReport, images) -> None:
        """按 id 逐项更新；仅 caption / is_selected / sort_order 可改，不涉及增删。"""
        existing = {img.id: img for img in report.images}
        for image_in in images:
            image = existing.get(image_in.id)
            if image is None:
                raise AppException(
                    "VALIDATION_ERROR", "图片不属于该报告", 400
                )
            if image_in.caption is not None:
                image.caption = image_in.caption
            if image_in.is_selected is not None:
                image.is_selected = image_in.is_selected
            if image_in.sort_order is not None:
                image.sort_order = image_in.sort_order

    @staticmethod
    def _to_list_item(report: PhotoReport) -> PhotoReportListItem:
        return PhotoReportListItem(
            id=report.id,
            title=report.title,
            inspection_unit=report.inspection_unit,
            status=report.status,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    @staticmethod
    def _to_detail(report: PhotoReport) -> PhotoReportDetail:
        return PhotoReportDetail(
            id=report.id,
            title=report.title,
            inspection_unit=report.inspection_unit,
            inspection_address=report.inspection_address,
            violation_summary=report.violation_summary,
            status=report.status,
            images=[
                PhotoReportImageResponse(
                    id=img.id,
                    uploaded_file_id=img.uploaded_file_id,
                    frame_timestamp=img.frame_timestamp,
                    caption=img.caption,
                    detected_address=img.detected_address,
                    detected_violation=img.detected_violation,
                    is_selected=img.is_selected,
                    sort_order=img.sort_order,
                    created_at=img.created_at,
                )
                for img in report.images
            ],
            source_task_id=report.source_task_id,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )
