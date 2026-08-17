"""向量库测试：存取、检索排序、按文档删除、游离清理支持。"""

import pytest

from app.core.exceptions import AppException
from app.rag.embedding.store import (
    ChunkRecord,
    ChromaVectorStore,
    LocalVectorStore,
)


def _record(index: int, content: str, vector: list[float], doc: str = "doc-a") -> ChunkRecord:
    return ChunkRecord(
        chunk_index=index,
        content=content,
        metadata={"document_id": doc, "article_number": f"第{index}条"},
        vector=vector,
    )


def test_upsert_and_search_ordering(tmp_path):
    store = LocalVectorStore(tmp_path)
    store.replace_document(
        "doc-a",
        [
            _record(0, "x 轴内容", [1.0, 0.0]),
            _record(1, "y 轴内容", [0.0, 1.0]),
            _record(2, "混合内容", [1.0, 1.0]),
        ],
    )
    results = store.search([1.0, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0].content == "x 轴内容"  # 完全一致得分最高
    assert results[0].score > results[1].score
    assert results[0].metadata["article_number"] == "第0条"


def test_replace_document_is_atomic_per_document(tmp_path):
    store = LocalVectorStore(tmp_path)
    store.replace_document("doc-a", [_record(0, "旧内容", [1.0, 0.0])])
    store.replace_document("doc-a", [_record(0, "新内容", [1.0, 0.0])])
    store.replace_document("doc-b", [_record(0, "其他文档", [0.0, 1.0])])
    assert store.count() == 2
    results = store.search([1.0, 0.0], top_k=10)
    contents = {r.content for r in results}
    assert "新内容" in contents
    assert "旧内容" not in contents  # 替换不产生重复 chunk


def test_delete_document(tmp_path):
    store = LocalVectorStore(tmp_path)
    store.replace_document("doc-a", [_record(0, "内容", [1.0, 0.0])])
    store.replace_document("doc-b", [_record(0, "内容", [1.0, 0.0])])
    store.delete_document("doc-a")
    assert store.list_document_ids() == ["doc-b"]
    assert all(r.document_id == "doc-b" for r in store.search([1.0, 0.0], top_k=10))


def test_search_empty_store(tmp_path):
    store = LocalVectorStore(tmp_path)
    assert store.search([1.0, 0.0], top_k=5) == []


def test_zero_query_vector_raises(tmp_path):
    store = LocalVectorStore(tmp_path)
    store.replace_document("doc-a", [_record(0, "内容", [1.0, 0.0])])
    with pytest.raises(AppException) as exc_info:
        store.search([0.0, 0.0], top_k=5)
    assert exc_info.value.code == "VECTOR_STORE_ERROR"


def test_chroma_provider_unavailable_readable(tmp_path, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "chromadb":
            raise ImportError("No module named 'chromadb'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(AppException) as exc_info:
        ChromaVectorStore(tmp_path)
    assert exc_info.value.code == "VECTOR_STORE_ERROR"
    assert "chroma" in exc_info.value.message.lower()
