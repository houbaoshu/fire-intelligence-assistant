"""Knowledge base application service.

Coordinates document upload -> validation -> storage -> indexing task; keeps
metadata, object storage and vector index in sync (specs/knowledge-base.md).
"""
from __future__ import annotations

import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.knowledge import KnowledgeDocument, KnowledgeIndexJob
from app.services.audit_service import AuditService
from app.services.file_service import FileService
from app.services.tasks.task_service import TaskService
from app.utils.file_validation import checksum_bytes, read_upload, validate_upload

logger = get_logger("knowledge")


class KnowledgeBaseService:
    def __init__(self, db: Session):
        self.db = db
        self.files = FileService(db)
        self.tasks = TaskService(db)
        self.audit = AuditService(db)

    def upload(self, user, file: UploadFile, title: str | None = None) -> tuple[KnowledgeDocument, uuid.UUID]:
        """Validate + store source document, create indexing task.

        Returns (document, task_id).
        """
        ext = validate_upload(file, "document")
        data = read_upload(file)
        checksum = checksum_bytes(data)

        # checksum duplicate detection (no silent duplicates)
        existing = self.db.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.checksum == checksum,
                KnowledgeDocument.deleted_at.is_(None),
                KnowledgeDocument.status.in_(["uploaded", "parsing", "indexing", "indexed"]),
            )
        )
        if existing is not None:
            raise ConflictError("该文档已存在于知识库中,请勿重复上传")

        doc_title = (title or "").strip() or (file.filename or "未命名文档")
        storage_path = f"knowledge/{uuid.uuid4()}{ext}"
        self.files.storage.save_bytes(storage_path, data)

        uploaded = self.files.store_bytes(
            data, "knowledge_source", file.filename or "document", user.id, mime=file.content_type
        )
        uploaded.storage_path = storage_path
        uploaded.category = "knowledge_source"

        document = KnowledgeDocument(
            title=doc_title,
            document_type=None,
            uploaded_file_id=uploaded.id,
            status="uploaded",
            checksum=checksum,
            created_by=user.id,
        )
        self.db.add(document)
        self.db.flush()

        task = self.tasks.create_task(
            "knowledge_indexing",
            user.id,
            input_data={"document_id": str(document.id)},
        )
        job = KnowledgeIndexJob(
            knowledge_document_id=document.id,
            ai_task_id=task.id,
            action="index",
            status="queued",
        )
        self.db.add(job)
        self.db.commit()

        self.audit.log(
            "knowledge_document.upload", user_id=user.id,
            entity_type="knowledge_document", entity_id=document.id,
        )
        self.db.commit()
        return document, task.id

    def list(self, *, page: int = 1, page_size: int = 20, status: str | None = None) -> tuple[list[KnowledgeDocument], int]:
        from sqlalchemy import func

        base = select(KnowledgeDocument).where(KnowledgeDocument.deleted_at.is_(None))
        count_base = select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.deleted_at.is_(None))
        if status:
            base = base.where(KnowledgeDocument.status == status)
            count_base = count_base.where(KnowledgeDocument.status == status)
        total = int(self.db.scalar(count_base) or 0)
        items = list(
            self.db.scalars(
                base.order_by(KnowledgeDocument.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return items, total

    def delete(self, user, document_id: uuid.UUID | str) -> KnowledgeDocument:
        """Soft-delete the metadata and remove vector index data."""
        document = self.db.get(KnowledgeDocument, uuid.UUID(str(document_id)))
        if document is None or document.deleted_at is not None:
            raise NotFoundError("知识文档不存在")
        document.deleted_at = _utcnow()
        # remove from vector index
        try:
            from app.rag.vectorstore.factory import get_vector_store

            get_vector_store().delete_document(str(document.id))
        except Exception as exc:  # noqa: BLE001
            logger.warning("vector delete failed for %s: %s", document.id, exc)
            raise ValidationError("向量索引删除失败,请稍后重试") from exc
        self.audit.log(
            "knowledge_document.delete", user_id=user.id,
            entity_type="knowledge_document", entity_id=document.id,
        )
        self.db.commit()
        return document

    def rebuild(self, user) -> uuid.UUID:
        """Full reindex: create a knowledge_reindexing task."""
        # only one equivalent rebuild at a time
        active = self.db.scalar(
            select(KnowledgeIndexJob).where(
                KnowledgeIndexJob.action == "full_rebuild",
                KnowledgeIndexJob.status.in_(["queued", "processing"]),
            )
        )
        if active is not None:
            raise ConflictError("已有重建任务正在进行中,请等待完成")
        task = self.tasks.create_task(
            "knowledge_reindexing",
            user.id,
            input_data={"scope": "all"},
        )
        job = KnowledgeIndexJob(action="full_rebuild", ai_task_id=task.id, status="queued")
        self.db.add(job)
        self.db.commit()
        self.audit.log(
            "knowledge_document.rebuild", user_id=user.id,
        )
        self.db.commit()
        return task.id

    def status(self) -> dict:
        return self._status_inner()

    def _status_inner(self) -> dict:
        from sqlalchemy import func

        total = int(self.db.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.deleted_at.is_(None))) or 0)
        indexed = int(self.db.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.status == "indexed", KnowledgeDocument.deleted_at.is_(None))) or 0)
        indexing = int(self.db.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.status.in_(["parsing", "indexing"]), KnowledgeDocument.deleted_at.is_(None))) or 0)
        failed = int(self.db.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.status == "failed", KnowledgeDocument.deleted_at.is_(None))) or 0)
        last = self.db.scalar(
            select(KnowledgeDocument.updated_at)
            .where(KnowledgeDocument.status == "indexed", KnowledgeDocument.deleted_at.is_(None))
            .order_by(KnowledgeDocument.updated_at.desc())
            .limit(1)
        )
        return {
            "document_count": total,
            "indexed_count": indexed,
            "indexing_count": indexing,
            "failed_count": failed,
            "last_indexed_at": last,
        }

    def accessible_document_ids(self, user) -> list[str] | None:
        """Document ids visible to the user; None means all (admin/supervisor)."""
        if user.role in ("admin", "supervisor"):
            return None
        # v1: inspector/viewer see indexed documents (knowledge is shared);
        # permission scoping is enforced server-side per specs/_common.md.
        return None


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
