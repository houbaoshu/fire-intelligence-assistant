"""知识库业务逻辑（API.md §6 / specs/knowledge-base.md）。

职责：文档列表/上传/删除/重建/聚合计数。协调关系元数据、对象存储、
向量索引三者同步；索引与重建经 ai_task 异步执行（TaskExecutor）。
"""

import hashlib
import os
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import conflict, not_found
from app.models.ai_task import AITask
from app.models.base import utc_now
from app.models.knowledge import KnowledgeDocument, KnowledgeIndexJob
from app.models.user import AuditLog, User
from app.repositories.knowledge_repository import (
    KnowledgeDocumentRepository,
    KnowledgeIndexJobRepository,
    aggregate_status_counts,
)
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import AuditLogRepository
from app.rag.embedding.store import get_vector_store
from app.services.file_service import FileService
from app.services.storage import StorageService
from app.services.tasks import get_task_executor


class KnowledgeBaseService:
    def __init__(self, session: Session, storage: StorageService | None = None) -> None:
        self.session = session
        self.documents = KnowledgeDocumentRepository(session)
        self.jobs = KnowledgeIndexJobRepository(session)
        self.tasks = TaskRepository(session)
        self.audit = AuditLogRepository(session)
        self.files = FileService(session, storage)
        self.settings = get_settings()

    def list_documents(
        self, status: str | None, page: int, page_size: int
    ) -> tuple[list[KnowledgeDocument], int]:
        return self.documents.list(status, page, page_size)

    def upload(
        self,
        *,
        user: User,
        filename: str | None,
        content_type: str | None,
        data: bytes,
        request_id: str | None = None,
    ) -> tuple[KnowledgeDocument, AITask]:
        """上传源文档：校验 → checksum 去重 → 存储 → 建文档/任务/索引 job（单事务）。

        重复内容检测（DATABASE.md：应尽量使用 checksum）：同 checksum 的未删除
        文档已存在时返回 409 DOCUMENT_DUPLICATE，不静默复用也不产生重复生效版本。
        """
        checksum = hashlib.sha256(data).hexdigest()
        existing = self.documents.find_by_checksum(checksum)
        if existing is not None:
            raise conflict(
                "DOCUMENT_DUPLICATE",
                f"相同内容的文档已存在：《{existing.title}》，请勿重复上传",
            )
        uploaded = self.files.save_upload(
            filename=filename or "",
            content_type=content_type,
            data=data,
            category="knowledge_source",
            uploaded_by=user.id,
            directory="knowledge",
        )
        title = os.path.splitext(os.path.basename(filename or ""))[0] or "未命名文档"
        document = KnowledgeDocument(
            title=title,
            document_type=(uploaded.file_extension or "").lstrip(".") or None,
            uploaded_file_id=uploaded.id,
            status="uploaded",
            checksum=checksum,
            doc_metadata={"original_name": uploaded.original_name},
            created_by=user.id,
        )
        self.documents.add(document)
        task = AITask(
            task_type="knowledge_indexing",
            status="pending",
            input_data={"document_id": str(document.id)},
            created_by=user.id,
        )
        self.tasks.add(task)
        self.jobs.add(
            KnowledgeIndexJob(
                knowledge_document_id=document.id,
                ai_task_id=task.id,
                action="index",
                status="pending",
            )
        )
        self.audit.append(
            AuditLog(
                user_id=user.id,
                action="knowledge_document.upload",
                entity_type="knowledge_document",
                entity_id=document.id,
                request_id=request_id,
                details={"task_id": str(task.id), "title": title},
            )
        )
        self.session.commit()
        self.session.refresh(document)
        self.session.refresh(task)
        get_task_executor().submit(task.id)
        return document, task

    def delete(
        self, user: User, document_id: uuid.UUID, request_id: str | None = None
    ) -> KnowledgeDocument:
        """软删除文档 + 移除向量索引 + delete_index job（DATABASE.md 事务规则）。

        先移除向量索引再提交关系元数据软删除；任一步失败回滚关系写入，
        文档保持可见以便恢复（specs/knowledge-base.md 删除规则）。
        """
        document = self.documents.get(document_id)
        if document is None:
            raise not_found("知识文档不存在")
        get_vector_store(self.settings).delete_document(str(document.id))
        document.deleted_at = utc_now()
        file = self.files.files.get(document.uploaded_file_id)
        if file is not None:
            file.deleted_at = utc_now()  # 源文件元数据软删除，存储对象保留待清理
        self.jobs.add(
            KnowledgeIndexJob(
                knowledge_document_id=document.id,
                action="delete_index",
                status="completed",
                indexed_chunks=0,
                completed_at=utc_now(),
            )
        )
        self.audit.append(
            AuditLog(
                user_id=user.id,
                action="knowledge_document.delete",
                entity_type="knowledge_document",
                entity_id=document.id,
                request_id=request_id,
                details={"title": document.title},
            )
        )
        self.session.commit()
        return document

    def rebuild(self, user: User, request_id: str | None = None) -> AITask:
        """全量重建索引（knowledge_reindexing 任务）；同一时刻只允许一个。"""
        if self.tasks.has_active_of_type("knowledge_reindexing"):
            raise conflict(
                "TASK_STATE_CONFLICT", "已有索引重建任务正在进行中，请等待完成后再试"
            )
        task = AITask(
            task_type="knowledge_reindexing",
            status="pending",
            input_data={},
            created_by=user.id,
        )
        self.tasks.add(task)
        self.jobs.add(
            KnowledgeIndexJob(ai_task_id=task.id, action="full_rebuild", status="pending")
        )
        self.audit.append(
            AuditLog(
                user_id=user.id,
                action="knowledge_base.rebuild",
                entity_type="knowledge_base",
                request_id=request_id,
                details={"task_id": str(task.id)},
            )
        )
        self.session.commit()
        self.session.refresh(task)
        get_task_executor().submit(task.id)
        return task

    def status(self) -> dict:
        """聚合计数 + last_indexed_at（无文档时计数 0、last_indexed_at null）。"""
        counts = aggregate_status_counts(self.documents.count_by_status())
        counts["last_indexed_at"] = self.documents.last_indexed_at()
        return counts
