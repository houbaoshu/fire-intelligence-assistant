"""索引管线编排（ARCHITECTURE.md §10.1）。

`源文档 → 解析 → 规范化 → 语义切分 → 元数据增强 → Embedding → 向量库`

同步更新 knowledge_documents 状态机与 chunk_count；knowledge_index_jobs
由调用方（任务 runner）落库。失败一律抛可读 ``AppException``，不吞错。

原子性约定：解析/切分/embedding 全部完成后才调用 ``store.replace_document``
（先删后写一次完成），管线中途失败不会破坏该文档最后可用的索引
（specs/knowledge-base.md「重建必须可恢复」）。
"""

import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.knowledge import KnowledgeDocument
from app.models.uploaded_file import UploadedFile
from app.rag.chunking import DocumentMeta, chunk_document
from app.rag.embedding.store import ChunkRecord, VectorStore, get_vector_store
from app.rag.parsers import parse_document
from app.services.ai.embedding import EmbeddingService
from app.services.storage import get_storage_service

logger = get_logger("rag.indexing")

# 进度回调：report(stage, progress)，由任务 runner 提供（含取消检查与单调性）
ProgressReporter = Callable[[str, int], None]


def _noop_report(_stage: str, _progress: int) -> None:
    pass


def index_document(
    session: Session,
    document_id: uuid.UUID,
    *,
    embedding: EmbeddingService | None = None,
    store: VectorStore | None = None,
    settings: Settings | None = None,
    report: ProgressReporter = _noop_report,
) -> int:
    """对单个知识文档执行完整索引管线，返回索引 chunk 数。"""
    s = settings or get_settings()
    embedding = embedding or EmbeddingService(s)
    store = store or get_vector_store(s)

    doc = session.get(KnowledgeDocument, document_id)
    if doc is None or doc.deleted_at is not None:
        raise AppException("DOCUMENT_NOT_FOUND", "知识文档不存在或已删除", 404)
    file = session.get(UploadedFile, doc.uploaded_file_id)
    if file is None:
        raise AppException("DOCUMENT_FILE_MISSING", "知识文档的源文件记录不存在", 500)

    report("parsing", 10)
    doc.status = "parsing"
    session.commit()
    try:
        data = get_storage_service().read(file.storage_path)
    except Exception:
        raise AppException(
            "DOCUMENT_FILE_MISSING", "源文件读取失败，请重新上传文档", 500
        )
    parsed = parse_document(file.file_extension or "", data)

    report("chunking", 30)
    doc.status = "indexing"
    session.commit()
    meta = DocumentMeta(
        document_id=str(doc.id),
        title=doc.title,
        document_type=doc.document_type,
        source_path=file.storage_path,
        version=doc.version,
        effective_date=doc.effective_date.isoformat() if doc.effective_date else None,
        issuing_authority=doc.issuing_authority,
    )
    chunks = chunk_document(parsed.blocks, meta)
    if not chunks:
        raise AppException(
            "DOCUMENT_EMPTY", "文档解析后无可用文本内容，无法建立索引", 400
        )

    report("embedding", 50)
    vectors = embedding.embed([c.content for c in chunks])

    report("vector_index", 90)
    store.replace_document(
        str(doc.id),
        [
            ChunkRecord(
                chunk_index=c.chunk_index,
                content=c.content,
                metadata=c.metadata,
                vector=vector,
            )
            for c, vector in zip(chunks, vectors, strict=True)
        ],
    )
    doc.status = "indexed"
    doc.chunk_count = len(chunks)
    session.commit()
    logger.info("知识文档 %s 索引完成：%d chunks", document_id, len(chunks))
    return len(chunks)


def rebuild_index(
    session: Session,
    *,
    embedding: EmbeddingService | None = None,
    store: VectorStore | None = None,
    settings: Settings | None = None,
    report: ProgressReporter = _noop_report,
) -> dict:
    """全量重建：清理游离 chunk 后逐文档重建（不产生重复生效 chunk）。

    逐文档 replace 语义保证：单文档失败只影响该文档状态，其余文档索引保持
    最后可用版本。返回 {"total", "indexed_chunks", "failures": [(title, message)]}。
    """
    s = settings or get_settings()
    embedding = embedding or EmbeddingService(s)
    store = store or get_vector_store(s)

    docs = list(
        session.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.deleted_at.is_(None))
            .order_by(KnowledgeDocument.created_at)
        )
        .scalars()
        .all()
    )
    active_ids = {str(d.id) for d in docs}
    for stale_id in store.list_document_ids():
        if stale_id not in active_ids:
            store.delete_document(stale_id)

    failures: list[tuple[str, str]] = []
    indexed_chunks = 0
    total = len(docs)
    for i, doc in enumerate(docs):
        base = 10 + int(80 * i / max(total, 1))
        try:
            indexed_chunks += index_document(
                session,
                doc.id,
                embedding=embedding,
                store=store,
                settings=s,
                report=lambda stage, p, base=base: report(stage, min(base + p // 10, 90)),
            )
        except AppException as exc:
            session.rollback()
            logger.info("重建中文档 %s 索引失败: %s %s", doc.id, exc.code, exc.message)
            doc = session.get(KnowledgeDocument, doc.id)
            if doc is not None and doc.deleted_at is None:
                doc.status = "failed"
                session.commit()
            failures.append((doc.title if doc else "未知文档", exc.message))
    return {"total": total, "indexed_chunks": indexed_chunks, "failures": failures}
