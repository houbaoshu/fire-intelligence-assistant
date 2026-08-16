"""Photo report application service."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.enums import RECORD_STATUSES
from app.models.photo_report import PhotoReport, PhotoReportImage
from app.schemas.photo_report import PhotoReportUpdate
from app.services.audit_service import AuditService
from app.services.file_service import FileService
from app.services.tasks.task_service import TaskService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PhotoReportService:
    def __init__(self, db: Session):
        self.db = db
        self.files = FileService(db)
        self.tasks = TaskService(db)
        self.audit = AuditService(db)

    def start_generation(self, user, video: UploadFile, remarks: str | None, idempotency_key: str | None = None) -> uuid.UUID:
        if idempotency_key:
            existing = self.tasks.find_by_idempotency_key(user.id, idempotency_key, "photo_report_generation")
            if existing is not None:
                return existing.id
        uploaded = self.files.store_upload(video, "video", user.id)
        report = PhotoReport(status="processing", created_by=user.id, title=remarks or "拍照报告")
        self.db.add(report)
        self.db.flush()
        task = self.tasks.create_task(
            "photo_report_generation",
            user.id,
            input_data={
                "report_id": str(report.id),
                "uploaded_file_id": str(uploaded.id),
                "remarks": remarks or "",
            },
            idempotency_key=idempotency_key,
        )
        self.db.commit()
        self.audit.log(
            "photo_report.create", user_id=user.id,
            entity_type="photo_report", entity_id=report.id,
        )
        self.db.commit()
        return task.id

    def _get_report(self, report_id: uuid.UUID | str) -> PhotoReport:
        report = self.db.get(PhotoReport, uuid.UUID(str(report_id)))
        if report is None or report.deleted_at is not None:
            raise NotFoundError("拍照报告不存在")
        return report

    def _check_view(self, user, report: PhotoReport) -> None:
        if user.role in ("admin", "supervisor"):
            return
        if report.created_by != user.id:
            raise ForbiddenError("无权访问该报告")

    def _check_edit(self, user, report: PhotoReport) -> None:
        if user.role in ("admin", "supervisor"):
            return
        if report.created_by != user.id:
            raise ForbiddenError("无权编辑该报告")

    def get(self, user, report_id: uuid.UUID | str) -> PhotoReport:
        report = self._get_report(report_id)
        self._check_view(user, report)
        return report

    def list(self, user, *, page: int = 1, page_size: int = 20, status: str | None = None) -> tuple[list[PhotoReport], int]:
        from sqlalchemy import func

        base = select(PhotoReport).where(PhotoReport.deleted_at.is_(None))
        count_base = select(func.count(PhotoReport.id)).where(PhotoReport.deleted_at.is_(None))
        if user.role not in ("admin", "supervisor"):
            base = base.where(PhotoReport.created_by == user.id)
            count_base = count_base.where(PhotoReport.created_by == user.id)
        if status:
            base = base.where(PhotoReport.status == status)
            count_base = count_base.where(PhotoReport.status == status)
        total = int(self.db.scalar(count_base) or 0)
        items = list(
            self.db.scalars(
                base.order_by(PhotoReport.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return items, total

    def update(self, user, report_id: uuid.UUID | str, payload: PhotoReportUpdate) -> PhotoReport:
        report = self._get_report(report_id)
        self._check_edit(user, report)

        if report.status == "finalized":
            content_fields = [payload.title, payload.inspection_unit, payload.inspection_address, payload.violation_summary, payload.images]
            if any(f is not None for f in content_fields):
                raise ConflictError("报告已定稿,不能直接修改内容")
            if payload.status not in (None, "archived"):
                raise ConflictError("报告已定稿,仅允许归档操作")

        data = payload.model_dump(exclude_unset=True)
        images_payload = data.pop("images", None)
        new_status = data.pop("status", None)
        for field, value in data.items():
            setattr(report, field, value)

        if images_payload is not None:
            self._update_images(report, images_payload)

        if new_status is not None:
            if new_status not in RECORD_STATUSES:
                raise ConflictError(f"非法状态:{new_status}")
            report.status = new_status
            if new_status == "finalized":
                if not any(img.is_selected for img in report.images):
                    raise ValidationError("报告至少需要一张选中的图片才能定稿")
                self._finalize(report, user)

        self.audit.log(
            "photo_report.update", user_id=user.id,
            entity_type="photo_report", entity_id=report.id,
        )
        self.db.commit()
        self.db.refresh(report)
        return report

    def _update_images(self, report: PhotoReport, images: list[dict]) -> None:
        existing = {str(img.id): img for img in report.images}
        for img_update in images:
            img_id = img_update.get("id")
            if not img_id:
                raise ValidationError("图片更新必须携带 id")
            img = existing.get(img_id)
            if img is None:
                raise ValidationError("图片 id 不属于该报告")
            for field in ("caption", "is_selected", "sort_order"):
                if field in img_update and img_update[field] is not None:
                    setattr(img, field, img_update[field])
        # normalize sort_order uniqueness
        selected = [img for img in report.images if img.is_selected]
        for order, img in enumerate(selected):
            img.sort_order = order

    def _finalize(self, report: PhotoReport, user) -> None:
        report.status = "finalized"
        self.audit.log(
            "photo_report.finalize", user_id=user.id,
            entity_type="photo_report", entity_id=report.id,
        )
        task = self.tasks.create_task(
            "document_generation",
            user.id,
            input_data={"entity_type": "photo_report", "entity_id": str(report.id)},
        )
        self.db.flush()

    def download(self, user, report_id: uuid.UUID | str) -> tuple[bytes, str]:
        from app.services.document_service import DocumentService

        report = self._get_report(report_id)
        self._check_view(user, report)
        return DocumentService(self.db).download_latest(
            user, entity_type="photo_report", entity_id=report.id,
            fallback_filename=f"photo-report-{report.id}.docx",
        )
