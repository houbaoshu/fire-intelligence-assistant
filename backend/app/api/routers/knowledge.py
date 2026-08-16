"""Knowledge base endpoints (API.md §6)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, UploadFile

from app.api.dependencies import CurrentUser, DB, require_roles
from app.schemas.knowledge import (
    KnowledgeDeleteResponse,
    KnowledgeDocumentListItem,
    KnowledgeDocumentListResponse,
    KnowledgeRebuildResponse,
    KnowledgeStatusResponse,
    KnowledgeUploadResponse,
)
from app.services.knowledge_service import KnowledgeBaseService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _doc_out(doc) -> KnowledgeDocumentListItem:
    return KnowledgeDocumentListItem(
        id=str(doc.id),
        title=doc.title,
        document_type=doc.document_type,
        status=doc.status,
        version=doc.version,
        issuing_authority=doc.issuing_authority,
        effective_date=doc.effective_date,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("/documents", response_model=KnowledgeDocumentListResponse)
def list_documents(
    user: CurrentUser,
    db: DB,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
):
    if page_size > 100:
        page_size = 100
    items, total = KnowledgeBaseService(db).list(
        page=page, page_size=page_size, status=status
    )
    return KnowledgeDocumentListResponse(
        items=[_doc_out(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/documents", response_model=KnowledgeUploadResponse)
def upload_document(
    user: CurrentUser,
    db: DB,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
):
    # upload/delete/rebuild require admin (specs/knowledge-base.md)
    require_roles("admin")(user)
    document, task_id = KnowledgeBaseService(db).upload(user, file, title)
    return KnowledgeUploadResponse(document_id=str(document.id), task_id=str(task_id))


@router.delete("/documents/{document_id}", response_model=KnowledgeDeleteResponse)
def delete_document(user: CurrentUser, db: DB, document_id: uuid.UUID):
    require_roles("admin")(user)
    KnowledgeBaseService(db).delete(user, document_id)
    return KnowledgeDeleteResponse(id=str(document_id), deleted=True)


@router.post("/rebuild", response_model=KnowledgeRebuildResponse)
def rebuild(user: CurrentUser, db: DB):
    require_roles("admin")(user)
    task_id = KnowledgeBaseService(db).rebuild(user)
    return KnowledgeRebuildResponse(task_id=str(task_id))


@router.get("/status", response_model=KnowledgeStatusResponse)
def status(user: CurrentUser, db: DB):
    data = KnowledgeBaseService(db).status()
    return KnowledgeStatusResponse(**data)
