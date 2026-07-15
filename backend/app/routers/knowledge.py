"""Knowledge base management endpoints."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_role
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import FileValidationException, NotFoundException
from app.core.logging import get_logger
from app.models.knowledge import KnowledgeDocument
from app.models.task import AITask
from app.models.user import User
from app.schemas.knowledge import KnowledgeDocumentListResponse, KnowledgeDocumentResponse

logger = get_logger(__name__)

router = APIRouter(tags=["knowledge"])

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx"}
TASK_TYPE = "knowledge_indexing"


def _validate_document(file: UploadFile) -> None:
    """Ensure the uploaded file is an allowed document type and within size limits."""
    settings = get_settings()

    if not file.filename:
        raise FileValidationException("Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise FileValidationException(
            f"Invalid file type '.{ext}'. Allowed types: "
            f"{', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}"
        )

    if file.size is not None and file.size > settings.max_upload_size_bytes:
        raise FileValidationException(
            f"File size ({file.size} bytes) exceeds the maximum allowed "
            f"({settings.max_upload_size_bytes} bytes)"
        )


async def _index_document(task_id: str, document_id: str) -> None:
    """Background task: parse and index a knowledge document.

    This is a placeholder that will be replaced by the actual service
    implementation. The service will:
    1. Parse the document (PDF/DOCX/PPTX)
    2. Chunk the text content
    3. Generate embeddings for each chunk
    4. Store chunks in the vector store (Chroma)
    5. Update the KnowledgeDocument status and chunk count
    6. Update the AITask status
    """
    from app.core.database import _get_session_factory
    from app.services.knowledge_service import KnowledgeService

    factory = _get_session_factory()
    async with factory() as db:
        try:
            service = KnowledgeService(db=db)
            await service.index_document(task_id=task_id, document_id=document_id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def _rebuild_index(task_id: str) -> None:
    """Background task: rebuild the entire knowledge index.

    This is a placeholder that will be replaced by the actual service
    implementation. The service will:
    1. Clear the existing vector store collection
    2. Re-index all active KnowledgeDocuments
    3. Update the AITask status
    """
    from app.core.database import _get_session_factory
    from app.services.knowledge_service import KnowledgeService

    factory = _get_session_factory()
    async with factory() as db:
        try:
            service = KnowledgeService(db=db)
            await service.rebuild_index(task_id=task_id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


@router.get(
    "/documents",
    response_model=KnowledgeDocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all knowledge documents",
)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentListResponse:
    """Return all non-deleted knowledge documents."""
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.deleted_at.is_(None))
        .order_by(KnowledgeDocument.created_at.desc())
    )
    documents = result.scalars().all()
    return KnowledgeDocumentListResponse(
        documents=[KnowledgeDocumentResponse.model_validate(doc) for doc in documents]
    )


@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a knowledge document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file (pdf/doc/docx/ppt/pptx)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentResponse:
    """Upload a document for knowledge base indexing.

    The file is validated, stored, and a KnowledgeDocument record is created.
    Indexing happens in the background.
    """
    _validate_document(file)

    # Save file to storage
    from app.services.storage_service import StorageService

    storage = StorageService()
    uploaded_file = await storage.save_upload(
        file=file, category="knowledge_source", user_id=str(current_user.id)
    )

    # Derive title from filename
    title = file.filename.rsplit(".", 1)[0] if file.filename else "Untitled"
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""

    # Create the knowledge document record
    doc = KnowledgeDocument(
        title=title,
        document_type=ext,
        uploaded_file_id=uploaded_file.id,
        status="uploaded",
        created_by=str(current_user.id),
    )
    db.add(doc)
    await db.flush()

    # Create an AI task for indexing
    task = AITask(
        task_type=TASK_TYPE,
        status="pending",
        progress=0,
        current_stage="parsing",
        input_data={"document_id": doc.id, "filename": file.filename},
        created_by=str(current_user.id),
    )
    db.add(task)
    await db.flush()

    logger.info(
        "Knowledge document uploaded: %s (doc_id=%s, task_id=%s) by user %s",
        file.filename,
        doc.id,
        task.id,
        current_user.id,
    )

    background_tasks.add_task(_index_document, task.id, doc.id)

    await db.refresh(doc)
    return KnowledgeDocumentResponse.model_validate(doc)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge document",
)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a knowledge document and remove it from the index."""
    from datetime import datetime

    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundException(f"Knowledge document '{document_id}' not found")

    # Soft delete
    doc.deleted_at = datetime.now(UTC)
    doc.status = "outdated"
    await db.flush()

    logger.info(
        "Knowledge document %s deleted by user %s",
        document_id,
        current_user.id,
    )


@router.post(
    "/rebuild",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Rebuild the entire knowledge index",
)
async def rebuild_index(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("admin", "supervisor")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Trigger a full rebuild of the knowledge base index.

    Only admin and supervisor roles are allowed to perform this operation.
    """
    task = AITask(
        task_type="knowledge_rebuild",
        status="pending",
        progress=0,
        current_stage="initializing",
        input_data={"action": "full_rebuild"},
        created_by=str(current_user.id),
    )
    db.add(task)
    await db.flush()

    logger.info(
        "Knowledge index rebuild initiated: task_id=%s by user %s",
        task.id,
        current_user.id,
    )

    background_tasks.add_task(_rebuild_index, task.id)

    return {"task_id": task.id}
