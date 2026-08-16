"""Knowledge indexing / reindexing pipeline.

Document -> parse -> chunk -> embed -> vector store -> mark indexed
(per AGENTS.md RAG flow and specs/knowledge-base.md).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.exceptions import AIProviderError, ValidationError
from app.models.knowledge import KnowledgeDocument, KnowledgeIndexJob
from app.rag.chunking.chunker import chunk_document
from app.rag.parsers.parser import parse_document
from app.rag.vectorstore.base import StoredChunk
from app.rag.vectorstore.factory import get_vector_store
from app.services.ai.embedding import EmbeddingService
from app.services.file_service import FileService
from app.services.tasks.registry import TaskContext, register_handler


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@register_handler("knowledge_indexing")
def handle_knowledge_indexing(ctx: TaskContext) -> None:
    document_id = uuid.UUID(ctx.input_data["document_id"])
    _index_single(ctx, document_id)


@register_handler("knowledge_reindexing")
def handle_knowledge_reindexing(ctx: TaskContext) -> None:
    from sqlalchemy import select

    store = get_vector_store()
    ctx.set_progress(5, "clearing_index")
    store.delete_all()
    docs = list(
        ctx.db.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.deleted_at.is_(None),
                KnowledgeDocument.status.in_(["indexed", "outdated", "failed", "uploaded"]),
            )
        ).all()
    )
    total = len(docs)
    for i, doc in enumerate(docs):
        ctx.set_progress(5 + int(90 * (i / max(total, 1))), "reindexing")
        job = _create_job(ctx, doc.id, "full_rebuild")
        try:
            _index_document(ctx, doc)
            job.status = "completed"
            job.indexed_chunks = doc.chunk_count or 0
            job.completed_at = _utcnow()
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error_message = str(exc)[:500]
            _mark_document_failed(doc, str(exc))
        ctx.db.commit()
    ctx.set_progress(100, None)
    ctx.set_result({"scope": "all", "documents": total})


def _create_job(ctx: TaskContext, doc_id: uuid.UUID | None, action: str) -> KnowledgeIndexJob:
    job = KnowledgeIndexJob(
        knowledge_document_id=doc_id,
        ai_task_id=ctx.task_id,
        action=action,
        status="processing",
    )
    ctx.db.add(job)
    return job


def _index_single(ctx: TaskContext, document_id: uuid.UUID) -> None:
    doc = ctx.db.get(KnowledgeDocument, document_id)
    if doc is None or doc.deleted_at is not None:
        raise ValidationError("知识文档不存在")
    job = _create_job(ctx, doc.id, "index")
    ctx.db.commit()
    try:
        _index_document(ctx, doc)
        doc.status = "indexed"
        job.status = "completed"
        job.indexed_chunks = doc.chunk_count or 0
        job.completed_at = _utcnow()
        ctx.set_result({"document_id": str(doc.id)})
    except Exception as exc:  # noqa: BLE001
        _mark_document_failed(doc, str(exc))
        job.status = "failed"
        job.error_message = str(exc)[:500]
        job.completed_at = _utcnow()
        ctx.set_result({"document_id": str(doc.id), "error": str(exc)[:200]})
    ctx.db.commit()


def _index_document(ctx: TaskContext, doc: KnowledgeDocument) -> None:
    file_service = FileService(ctx.db)
    uploaded = file_service.get_record(doc.uploaded_file_id)
    if uploaded is None:
        raise ValidationError("源文件不存在")
    data = file_service.storage.open_bytes(uploaded.storage_path)
    ext = uploaded.file_extension or ""

    ctx.set_progress(25, "parsing")
    parsed = parse_document(data, ext)

    ctx.set_progress(45, "chunking")
    doc_metadata = {
        "document_id": str(doc.id),
        "title": doc.title,
        "document_type": doc.document_type or "",
        "version": doc.version or "",
        "effective_date": str(doc.effective_date) if doc.effective_date else "",
        "issuing_authority": doc.issuing_authority or "",
        "source": uploaded.original_name,
    }
    chunks = chunk_document(parsed.text, doc_metadata=doc_metadata)

    ctx.set_progress(60, "embedding")
    embedding_service = EmbeddingService()
    texts = [c.text for c in chunks]
    vectors = embedding_service.embed(texts)

    ctx.set_progress(85, "indexing")
    store = get_vector_store()
    stored = [
        StoredChunk(
            chunk_id=f"{doc.id}-{i}",
            document_id=str(doc.id),
            text=c.text,
            embedding=vectors[i],
            metadata=c.metadata,
        )
        for i, c in enumerate(chunks)
    ]
    store.upsert_chunks(stored)
    doc.chunk_count = len(stored)


def _mark_document_failed(doc: KnowledgeDocument, message: str) -> None:
    doc.status = "failed"
    if doc.doc_metadata is None:
        doc.doc_metadata = {}
    doc.doc_metadata["last_error"] = message[:500]
