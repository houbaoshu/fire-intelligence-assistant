"""Word 文档渲染（docxtpl 模板，模板文件在 backend/data/templates/）。

下载语义（M2 决策，README 有记录）：download 时按已保存结构化数据即时渲染，
每次渲染产生新的 generated_documents 版本（version 递增，历史版本保留不覆盖），
保证文书内容与已保存的审阅版本一致；渲染不满足业务规则（如拍照报告无选中
图片）返回 409 DOCUMENT_NOT_READY。
"""

import io
import uuid
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.generated_document import GeneratedDocument
from app.models.inspection import InspectionRecord
from app.models.interview import InterviewRecord
from app.models.photo_report import PhotoReport
from app.repositories.file_repository import GeneratedDocumentRepository
from app.services.file_service import FileService
from app.services.storage import StorageService

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "data" / "templates"

_TEMPLATES = {
    "inspection_record": "inspection_record.docx",
    "photo_report": "photo_report.docx",
    "interview_record": "interview_record.docx",
}

_DOCUMENT_TYPES = {
    "inspection_record": "inspection_record_docx",
    "photo_report": "photo_report_docx",
    "interview_record": "interview_record_docx",
}


def _fmt_datetime(value) -> str:
    return value.strftime("%Y年%m月%d日 %H:%M") if value else ""


def _fmt_date(value) -> str:
    return value.strftime("%Y年%m月%d日") if value else ""


class DocumentGenerationService:
    def __init__(self, session: Session, storage: StorageService | None = None) -> None:
        self.session = session
        self.documents = GeneratedDocumentRepository(session)
        self.files = FileService(session, storage)

    def generate(
        self,
        *,
        entity_type: str,
        entity,
        created_by: uuid.UUID,
        task_id: uuid.UUID | None = None,
    ) -> tuple[str, bytes, GeneratedDocument]:
        """渲染并入库一个新版本，返回 (下载文件名, 文件字节, 元数据)。不提交事务。"""
        template_path = TEMPLATE_DIR / _TEMPLATES[entity_type]
        tpl = DocxTemplate(str(template_path))
        context = self._build_context(tpl, entity_type, entity)
        buffer = io.BytesIO()
        tpl.render(context)
        tpl.save(buffer)
        data = buffer.getvalue()

        filename = self._download_filename(entity_type, entity)
        uploaded = self.files.save_generated(
            filename=filename, data=data, uploaded_by=created_by
        )
        document = GeneratedDocument(
            document_type=_DOCUMENT_TYPES[entity_type],
            source_entity_type=entity_type,
            source_entity_id=entity.id,
            uploaded_file_id=uploaded.id,
            version=self.documents.next_version(entity_type, entity.id),
            generated_by_task_id=task_id,
            created_by=created_by,
        )
        self.documents.add(document)
        return filename, data, document

    # ---------- 模板数据映射（结构化记录是事实源，字段缺失留空，禁止编造） ----------

    def _build_context(
        self, tpl: DocxTemplate, entity_type: str, entity
    ) -> dict[str, Any]:
        if entity_type == "inspection_record":
            return self._inspection_context(entity)
        if entity_type == "photo_report":
            return self._photo_report_context(tpl, entity)
        if entity_type == "interview_record":
            return self._interview_context(entity)
        raise ValueError(f"未知文档实体类型: {entity_type}")

    def _inspection_context(self, record: InspectionRecord) -> dict[str, Any]:
        items = sorted(record.items, key=lambda i: i.sort_order)
        return {
            "title": record.title or "消防检查记录",
            "record_number": record.record_number or "",
            "inspection_unit": record.inspection_unit or "",
            "inspection_address": record.inspection_address or "",
            "inspection_date": _fmt_date(record.inspection_date),
            "inspector_names": "、".join(record.inspector_names or []),
            "contact_person": record.contact_person or "",
            "contact_phone": record.contact_phone or "",
            "items": [
                {
                    "sort_order": item.sort_order,
                    "item_type": item.item_type,
                    "location": item.location or "",
                    "description": item.description,
                    "legal_basis": item.legal_basis or "",
                    "correction_requirement": item.correction_requirement or "",
                    "severity": item.severity or "",
                }
                for item in items
            ],
            "summary": record.summary or "",
            "conclusion": record.conclusion or "",
        }

    def _photo_report_context(self, tpl: DocxTemplate, report: PhotoReport) -> dict[str, Any]:
        selected = sorted(
            (img for img in report.images if img.is_selected),
            key=lambda i: i.sort_order,
        )
        if not selected:
            raise AppException(
                "DOCUMENT_NOT_READY", "报告没有已选中的图片，无法生成文档", 409
            )
        images = []
        for img in selected:
            uploaded = self.files.files.get(img.uploaded_file_id)
            if uploaded is None:
                raise AppException(
                    "DOCUMENT_NOT_READY", "报告引用的图片文件不存在，无法生成文档", 409
                )
            image_bytes = self.files.read_bytes(uploaded)
            images.append(
                {
                    "image": InlineImage(tpl, io.BytesIO(image_bytes), width=Mm(140)),
                    "caption": img.caption or "",
                    "frame_timestamp": img.frame_timestamp,
                    "detected_address": img.detected_address or "",
                    "detected_violation": img.detected_violation or "",
                }
            )
        return {
            "title": report.title or "消防检查拍照报告",
            "inspection_unit": report.inspection_unit or "",
            "inspection_address": report.inspection_address or "",
            "violation_summary": report.violation_summary or "",
            "images": images,
        }

    def _interview_context(self, record: InterviewRecord) -> dict[str, Any]:
        qa = (record.structured_content or {}).get("questions_and_answers") or []
        return {
            "title": record.title or "询问记录",
            "interviewee_name": record.interviewee_name or "",
            "interviewer_names": "、".join(record.interviewer_names or []),
            "location": record.location or "",
            "started_at": _fmt_datetime(record.started_at),
            "ended_at": _fmt_datetime(record.ended_at),
            "transcript": record.transcript or "",
            "questions_and_answers": [
                {"question": str(q.get("question", "")), "answer": str(q.get("answer", ""))}
                for q in qa
                if isinstance(q, dict)
            ],
        }

    @staticmethod
    def _download_filename(entity_type: str, entity) -> str:
        """下载文件名规则见 API.md §4（ASCII 安全，避免 Content-Disposition 编码问题）。"""
        if entity_type == "inspection_record":
            suffix = entity.record_number or str(entity.id)
            return f"inspection-record-{suffix}.docx"
        if entity_type == "photo_report":
            return f"photo-report-{entity.id}.docx"
        return f"interview-record-{entity.id}.docx"
