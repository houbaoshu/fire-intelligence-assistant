"""Knowledge base service."""

from __future__ import annotations

import hashlib
from datetime import UTC
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import FileValidationException, NotFoundException
from app.core.logging import get_logger
from app.models.file import UploadedFile
from app.models.knowledge import KnowledgeDocument
from app.models.task import AITask
from app.models.user import User
from app.services.storage.factory import get_storage_service

logger = get_logger(__name__)

# Allowed document extensions
ALLOWED_DOC_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}
ALLOWED_DOC_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "text/markdown",
}


class KnowledgeService:
    """Service for knowledge base operations."""

    async def list_documents(
        self,
        db: AsyncSession,
    ) -> list[KnowledgeDocument]:
        """List all knowledge documents.

        Args:
            db: Database session.

        Returns:
            List of KnowledgeDocument instances.
        """
        result = await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.deleted_at.is_(None))
            .order_by(KnowledgeDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def upload_document(
        self,
        file: UploadFile,
        user: User,
        db: AsyncSession,
    ) -> KnowledgeDocument:
        """Upload a knowledge document.

        Args:
            file: Uploaded document file.
            user: Current user.
            db: Database session.

        Returns:
            Created KnowledgeDocument.

        Raises:
            FileValidationException: If file is invalid.
        """
        logger.info("Knowledge document upload", extra={"user_id": str(user.id)})

        # Validate file
        if not file.filename:
            raise FileValidationException("Filename is required")

        ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_DOC_EXTENSIONS:
            raise FileValidationException(
                f"Invalid file extension. Allowed: {', '.join(ALLOWED_DOC_EXTENSIONS)}"
            )

        if file.content_type and file.content_type not in ALLOWED_DOC_MIMES:
            raise FileValidationException(
                f"Invalid MIME type. Allowed: {', '.join(ALLOWED_DOC_MIMES)}"
            )

        # Read file content
        content = await file.read()
        settings = get_settings()
        if len(content) > settings.max_upload_size_bytes:
            raise FileValidationException(
                f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
            )

        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Save to storage
        storage = get_storage_service()
        file_id = str(uuid4())
        storage_path = f"knowledge/{file_id}{ext}"
        await storage.upload(content, storage_path, file.content_type)

        # Create UploadedFile record
        uploaded_file = UploadedFile(
            id=file_id,
            original_name=file.filename,
            storage_path=storage_path,
            storage_provider=settings.storage_provider,
            mime_type=file.content_type,
            file_extension=ext,
            size_bytes=len(content),
            checksum=checksum,
            category="knowledge_source",
            uploaded_by=str(user.id),
        )
        db.add(uploaded_file)

        # Create KnowledgeDocument
        doc = KnowledgeDocument(
            title=file.filename,
            document_type=ext.lstrip("."),
            uploaded_file_id=file_id,
            status="uploaded",
            checksum=checksum,
            created_by=str(user.id),
        )
        db.add(doc)
        await db.flush()

        logger.info("Knowledge document uploaded", extra={"doc_id": doc.id})

        return doc

    async def delete_document(
        self,
        doc_id: str,
        user: User,
        db: AsyncSession,
    ) -> None:
        """Soft-delete a knowledge document.

        Args:
            doc_id: Document UUID.
            user: Current user.
            db: Database session.

        Raises:
            NotFoundException: If document not found.
        """
        from datetime import datetime

        result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        doc = result.scalar_one_or_none()

        if not doc:
            raise NotFoundException("Knowledge document not found")

        doc.deleted_at = datetime.now(UTC)
        await db.flush()

        logger.info("Knowledge document deleted", extra={"doc_id": doc_id})

    async def rebuild_index(
        self,
        user: User,
        db: AsyncSession,
    ) -> AITask:
        """Trigger a full index rebuild for all knowledge documents.

        Args:
            user: Current user.
            db: Database session.

        Returns:
            Created AITask.
        """
        logger.info("Knowledge index rebuild requested", extra={"user_id": str(user.id)})

        task = AITask(
            task_type="knowledge_full_rebuild",
            status="pending",
            input_data={"action": "full_rebuild"},
            created_by=str(user.id),
        )
        db.add(task)
        await db.flush()

        return task

    async def index_document(
        self,
        doc_id: str,
        task_id: str,
    ) -> None:
        """Background task: parse, chunk, embed, and store document in vector DB.

        This method is called by the task executor.

        Args:
            doc_id: KnowledgeDocument UUID.
            task_id: AITask UUID.
        """
        from app.services.tasks.executor import TaskExecutor

        executor = TaskExecutor()
        await executor.execute_knowledge_indexing(task_id, doc_id)
