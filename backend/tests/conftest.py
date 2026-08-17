"""测试夹具：临时 SQLite 库（走 Alembic migration 建表）+ FastAPI TestClient。"""

import os
import tempfile
from pathlib import Path

# 必须在导入 app 之前设置环境变量（settings 经 lru_cache 缓存）
_tmp_dir = tempfile.mkdtemp(prefix="fire-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["JWT_SECRET"] = "test-secret-key-for-pytest-only-32bytes"
os.environ["STORAGE_DIR"] = str(Path(_tmp_dir) / "storage")
os.environ["VECTOR_STORE_DIR"] = str(Path(_tmp_dir) / "vectorstore")

import pytest
from fastapi.testclient import TestClient

from alembic import command
from alembic.config import Config

from app.api.dependencies import get_db
from app.db import create_engine_from_url
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent

_engine = create_engine_from_url(os.environ["DATABASE_URL"])


def _run_migrations() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")


_run_migrations()


@pytest.fixture(autouse=True)
def clean_tables():
    """每个测试结束后清空业务表与向量库，保证测试隔离。"""
    yield
    from app.models.ai_task import AITask
    from app.models.generated_document import GeneratedDocument
    from app.models.inspection import InspectionRecord, InspectionRecordItem
    from app.models.interview import InterviewRecord
    from app.models.knowledge import KnowledgeDocument, KnowledgeIndexJob
    from app.models.photo_report import PhotoReport, PhotoReportImage
    from app.models.uploaded_file import UploadedFile
    from app.models.user import AuditLog, User, UserProfile
    from app.rag.embedding.store import get_vector_store

    store = get_vector_store()
    for document_id in store.list_document_ids():
        store.delete_document(document_id)

    with _engine.begin() as conn:
        for table in (
            KnowledgeIndexJob,
            KnowledgeDocument,
            GeneratedDocument,
            PhotoReportImage,
            PhotoReport,
            InspectionRecordItem,
            InspectionRecord,
            InterviewRecord,
            AITask,
            UploadedFile,
            AuditLog,
            UserProfile,
            User,
        ):
            conn.execute(table.__table__.delete())


@pytest.fixture
def client():
    from sqlalchemy.orm import sessionmaker

    TestSession = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
