from __future__ import annotations

import uuid
from typing import cast

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.permissions import authorized_user_ids, require_permission
from app.db.models import AITask, KnowledgeChunk, KnowledgeDocument, UploadedFile, User, utc_now
from app.db.session import get_db
from app.rag import RetrievalService
from app.schemas.business import (
    KnowledgeDocumentResponse,
    KnowledgeUploadResponse,
    QARequest,
    QAResponse,
    QASource,
    TaskCreateResponse,
)
from app.services.ai import AIOrchestrator, OpenAICompatibleClient
from app.services.audit import add_audit_log
from app.services.files import persist_upload
from app.services.storage import StorageProvider
from app.services.tasks import TaskDispatcher, TaskService

router = APIRouter(tags=["knowledge"])
DOCUMENT_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".ppt", ".pptx"})


def knowledge_response(
    document: KnowledgeDocument, uploaded: UploadedFile, task_id: uuid.UUID | None = None
) -> KnowledgeDocumentResponse:
    return KnowledgeDocumentResponse(
        id=document.id,
        title=document.title,
        name=uploaded.original_name,
        document_type=document.document_type,
        status=document.status,
        version=document.version,
        issuing_authority=document.issuing_authority,
        effective_date=document.effective_date,
        expiration_date=document.expiration_date,
        chunk_count=document.chunk_count,
        error=document.error_message,
        task_id=task_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get("/knowledge/documents", response_model=list[KnowledgeDocumentResponse])
def list_documents(
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.read")),
) -> list[KnowledgeDocumentResponse]:
    statement = (
        select(KnowledgeDocument, UploadedFile)
        .join(UploadedFile, UploadedFile.id == KnowledgeDocument.uploaded_file_id)
        .where(KnowledgeDocument.deleted_at.is_(None))
        .order_by(KnowledgeDocument.updated_at.desc())
    )
    visible = authorized_user_ids(session, user)
    if visible is not None:
        statement = statement.where(KnowledgeDocument.created_by.in_(visible))
    rows = session.execute(statement).all()
    return [knowledge_response(document, uploaded) for document, uploaded in rows]


@router.post(
    "/knowledge/documents",
    response_model=KnowledgeUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.manage")),
) -> KnowledgeUploadResponse:
    uploaded = persist_upload(
        session,
        cast(StorageProvider, request.app.state.storage),
        file,
        user_id=user.id,
        category="knowledge_source",
        storage_category="knowledge",
        extensions=DOCUMENT_EXTENSIONS,
        max_bytes=request.app.state.settings.max_document_bytes,
    )
    duplicate = session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.checksum == uploaded.checksum,
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if duplicate:
        cast(StorageProvider, request.app.state.storage).delete(uploaded.storage_path)
        session.rollback()
        raise AppError(
            status_code=409,
            code="DUPLICATE_KNOWLEDGE_DOCUMENT",
            message="This document is already present in the knowledge base.",
            details={"document_id": str(duplicate.id)},
        )
    document = KnowledgeDocument(
        title=uploaded.original_name.rsplit(".", 1)[0],
        document_type=(uploaded.file_extension or "").lstrip("."),
        uploaded_file_id=uploaded.id,
        status="uploaded",
        checksum=uploaded.checksum,
        created_by=user.id,
    )
    session.add(document)
    session.flush()
    task = TaskService(session).create(
        task_type="knowledge_indexing",
        user_id=user.id,
        input_data={"document_id": str(document.id)},
        result_data={"entity_type": "knowledge_document", "entity_id": str(document.id)},
    )
    add_audit_log(
        session,
        user_id=user.id,
        action="knowledge_document.upload",
        entity_type="knowledge_document",
        entity_id=document.id,
        request_id=getattr(request.state, "request_id", None),
    )
    session.commit()
    cast(TaskDispatcher, request.app.state.task_dispatcher).submit(task.id)
    return KnowledgeUploadResponse(
        document=knowledge_response(document, uploaded, task.id), task_id=task.id
    )


@router.delete("/knowledge/documents/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.manage")),
) -> None:
    document = session.get(KnowledgeDocument, document_id)
    if document is None or document.deleted_at is not None:
        raise AppError(
            status_code=404,
            code="KNOWLEDGE_DOCUMENT_NOT_FOUND",
            message="Knowledge document not found.",
        )
    visible = authorized_user_ids(session, user)
    if visible is not None and document.created_by not in visible:
        raise AppError(
            status_code=404,
            code="KNOWLEDGE_DOCUMENT_NOT_FOUND",
            message="Knowledge document not found.",
        )
    document.deleted_at = utc_now()
    document.status = "outdated"
    session.execute(
        delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_document_id == document.id)
    )
    add_audit_log(
        session,
        user_id=user.id,
        action="knowledge_document.delete",
        entity_type="knowledge_document",
        entity_id=document.id,
        request_id=getattr(request.state, "request_id", None),
    )
    session.commit()


@router.post("/knowledge/rebuild", response_model=TaskCreateResponse, status_code=202)
def rebuild_index(
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.manage")),
) -> TaskCreateResponse:
    active = session.scalar(
        select(AITask).where(
            AITask.task_type == "knowledge_reindexing",
            AITask.status.in_(("pending", "queued", "processing")),
        )
    )
    if active:
        return TaskCreateResponse(task_id=active.id)
    visible = authorized_user_ids(session, user)
    statement = select(KnowledgeDocument.id).where(KnowledgeDocument.deleted_at.is_(None))
    if visible is not None:
        statement = statement.where(KnowledgeDocument.created_by.in_(visible))
    document_ids = [str(value) for value in session.scalars(statement)]
    task = TaskService(session).create(
        task_type="knowledge_reindexing",
        user_id=user.id,
        input_data={"document_ids": document_ids},
    )
    add_audit_log(
        session,
        user_id=user.id,
        action="knowledge_index.rebuild",
        entity_type="knowledge_index",
        request_id=getattr(request.state, "request_id", None),
    )
    session.commit()
    cast(TaskDispatcher, request.app.state.task_dispatcher).submit(task.id)
    return TaskCreateResponse(task_id=task.id)


@router.post("/qa/query", response_model=QAResponse)
def query_regulations(
    payload: QARequest,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.read")),
) -> QAResponse:
    question = payload.question.strip()
    if not question:
        raise AppError(status_code=422, code="EMPTY_QUESTION", message="Enter a question.")
    retrieved = RetrievalService(session, request.app.state.settings).search(
        question, creator_ids=authorized_user_ids(session, user)
    )
    if not retrieved:
        return QAResponse(
            answer="当前知识库未检索到足够的法规证据，无法给出确定结论。请补充或更新权威法规文档后重试。",
            sources=[],
            evidence_status="no_evidence",
        )
    sources = [
        QASource.model_validate(RetrievalService.source_reference(item)) for item in retrieved
    ]
    client = OpenAICompatibleClient(request.app.state.settings)
    if client.is_configured("llm"):
        answer = AIOrchestrator(client).grounded_answer(
            question, [item.chunk.content for item in retrieved]
        )
        evidence_status = "grounded"
    else:
        excerpts = "\n\n".join(
            f"[{index}] {source.excerpt}" for index, source in enumerate(sources, 1)
        )
        answer = (
            f"当前环境未配置语言模型。以下是检索到的相关法规原文，需由检查人员核对：\n\n{excerpts}"
        )
        evidence_status = "retrieval_only"
    return QAResponse(answer=answer, sources=sources, evidence_status=evidence_status)
