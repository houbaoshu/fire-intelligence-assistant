"""知识库路由（API.md §6）。保持薄：解析请求、调用 KnowledgeBaseService。

权限（specs/knowledge-base.md）：上传/删除/重建仅 admin；查询类端点所有认证用户。
"""

import uuid

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile

from app.api.dependencies import CurrentUser, DbSession, get_request_id, require_roles
from app.models.user import User
from app.schemas.common import Page
from app.schemas.knowledge import (
    DocumentStatus,
    KnowledgeDeleteResponse,
    KnowledgeDocumentListItem,
    KnowledgeRebuildResponse,
    KnowledgeStatusResponse,
    KnowledgeUploadResponse,
)
from app.services.knowledge_service import KnowledgeBaseService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

AdminUser = Depends(require_roles("admin"))


def _to_list_item(doc) -> KnowledgeDocumentListItem:
    return KnowledgeDocumentListItem(
        id=doc.id,
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


@router.get("/documents", response_model=Page[KnowledgeDocumentListItem])
def list_documents(
    session: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: DocumentStatus | None = None,
) -> Page[KnowledgeDocumentListItem]:
    rows, total = KnowledgeBaseService(session).list_documents(
        str(status) if status else None, page, page_size
    )
    return Page(
        items=[_to_list_item(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/documents", response_model=KnowledgeUploadResponse)
def upload_document(
    session: DbSession,
    request: Request,
    current_user: User = AdminUser,
    file: UploadFile = File(...),
) -> KnowledgeUploadResponse:
    document, task = KnowledgeBaseService(session).upload(
        user=current_user,
        filename=file.filename,
        content_type=file.content_type,
        data=file.file.read(),
        request_id=get_request_id(request),
    )
    return KnowledgeUploadResponse(document_id=document.id, task_id=task.id)


@router.delete("/documents/{document_id}", response_model=KnowledgeDeleteResponse)
def delete_document(
    document_id: uuid.UUID,
    session: DbSession,
    request: Request,
    current_user: User = AdminUser,
) -> KnowledgeDeleteResponse:
    document = KnowledgeBaseService(session).delete(
        current_user, document_id, request_id=get_request_id(request)
    )
    return KnowledgeDeleteResponse(id=document.id, deleted=True)


@router.post("/rebuild", response_model=KnowledgeRebuildResponse)
def rebuild_index(
    session: DbSession,
    request: Request,
    current_user: User = AdminUser,
) -> KnowledgeRebuildResponse:
    task = KnowledgeBaseService(session).rebuild(
        current_user, request_id=get_request_id(request)
    )
    return KnowledgeRebuildResponse(task_id=task.id)


@router.get("/status", response_model=KnowledgeStatusResponse)
def knowledge_status(session: DbSession, current_user: CurrentUser) -> dict:
    return KnowledgeBaseService(session).status()
