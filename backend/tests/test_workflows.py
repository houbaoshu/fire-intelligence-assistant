from __future__ import annotations

from io import BytesIO
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import AITask, KnowledgeChunk, KnowledgeDocument, UploadedFile, User
from app.services import workflows
from app.services.tasks import TaskContext


def test_knowledge_embeddings_are_sent_in_batches_of_ten(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    batches: list[list[str]] = []

    class FakeEmbeddingClient:
        def __init__(self, _: Any) -> None:
            pass

        def is_configured(self, capability: str) -> bool:
            return capability == "embedding"

        def embed(self, texts: list[str]) -> list[list[float]]:
            batches.append(texts)
            return [[float(len(text))] for text in texts]

    chunks = [(f"chunk-{index}", {"index": index}) for index in range(21)]
    monkeypatch.setattr(workflows, "OpenAICompatibleClient", FakeEmbeddingClient)
    monkeypatch.setattr(workflows, "parse_document", lambda *_: [("source", {})])
    monkeypatch.setattr(workflows, "chunk_sections", lambda *_, **__: chunks)

    application = client.app
    stored = application.state.storage.save(
        category="knowledge", filename="knowledge.pdf", source=BytesIO(b"source")
    )
    with application.state.session_factory() as session:
        user = User(email="batch-test@example.com", role="admin", is_active=True)
        session.add(user)
        session.flush()
        uploaded = UploadedFile(
            original_name="knowledge.pdf",
            storage_path=stored.path,
            storage_provider="local",
            mime_type="application/pdf",
            file_extension=".pdf",
            size_bytes=stored.size_bytes,
            category="knowledge_source",
            uploaded_by=user.id,
        )
        session.add(uploaded)
        session.flush()
        document = KnowledgeDocument(
            title="Knowledge",
            document_type="pdf",
            uploaded_file_id=uploaded.id,
            status="uploaded",
            created_by=user.id,
        )
        task = AITask(task_type="knowledge_indexing", created_by=user.id)
        session.add_all([document, task])
        session.commit()

        count = workflows._index_document(TaskContext(session, task, application.state), document)

        assert count == 21
        assert [len(batch) for batch in batches] == [10, 10, 1]
        persisted = session.scalars(
            select(KnowledgeChunk).order_by(KnowledgeChunk.chunk_index)
        ).all()
        assert len(persisted) == 21
        assert all(chunk.embedding is not None for chunk in persisted)
