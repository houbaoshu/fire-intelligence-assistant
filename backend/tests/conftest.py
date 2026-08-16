"""Shared test fixtures: isolated SQLite database + TestClient."""
from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Point settings at an isolated database BEFORE importing app modules
_tmpdir = tempfile.mkdtemp(prefix="fip-test-")
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["STORAGE_LOCAL_ROOT"] = f"{_tmpdir}/storage"
os.environ["TASK_WORKER_IN_PROCESS"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-32-bytes-long-enough-for-hmac"
os.environ["REGISTRATION_ENABLED"] = "true"

from app.core.config import reload_settings  # noqa: E402

reload_settings()

from app.core.database import SessionLocal, dispose_engine, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DIR = Path(_tmpdir)


@pytest.fixture(scope="session", autouse=True)
def _db_setup():
    init_db()
    yield
    dispose_engine()


@pytest.fixture(autouse=True)
def _clean_state():
    """Fresh tables + storage + vector store for every test."""
    from app.models import Base

    from app.rag.vectorstore.factory import get_vector_store

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    shutil.rmtree(TEST_DIR / "storage", ignore_errors=True)
    (TEST_DIR / "storage").mkdir(parents=True, exist_ok=True)
    try:
        get_vector_store().delete_all()
    except Exception:
        pass
    yield
    # also clean the per-test sqlite vector store file if the provider switched
    try:
        from app.core.config import get_settings

        (get_settings().data_dir / "vector_store.sqlite").unlink(missing_ok=True)
    except Exception:
        pass


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    """Register a fresh unique user; returns (headers, user) per call."""

    def _make(role: str = "inspector") -> tuple[dict, dict]:
        email = f"{role}-{uuid.uuid4().hex[:10]}@test.com"
        payload = {"email": email, "password": "password123", "full_name": "测试用户"}
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, r.json()["user"]

    return _make


@pytest.fixture()
def admin_headers(client):
    """Register a fresh admin user directly in the DB (registration is inspector-only)."""
    from app.core.security import hash_password
    from app.models.user import User, UserProfile

    db = SessionLocal()
    try:
        u = User(
            email=f"admin-{uuid.uuid4().hex[:10]}@test.com",
            password_hash=hash_password("password123"),
            role="admin",
        )
        db.add(u)
        db.flush()
        db.add(UserProfile(user_id=u.id, full_name="管理员"))
        db.commit()
        user_id = u.id
    finally:
        db.close()
    from app.core.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}, {"id": str(user_id), "role": "admin"}

# ---------------------------------------------------------------------------
# Mocked OpenAI-compatible provider (shared by AI pipeline / QA / evaluation tests)
# ---------------------------------------------------------------------------

import json

import httpx


def _msg_text(message: dict) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def _ai_transport_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/chat/completions"):
        body = json.loads(request.content)
        user_text = " ".join(_msg_text(m) for m in body.get("messages", []))
        if "消防检查记录" in user_text or "结构化检查记录" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"title": "某商场消防检查记录", "inspection_unit": "某商场", "inspection_address": "某市某区某路 1 号", "inspection_date": "2026-01-01", "inspector_names": ["张三"], "summary": "概述", "conclusion": "结论", "items": [{"item_type": "violation", "location": "一层", "description": "安全出口被锁闭", "legal_basis": "消防法第二十八条", "severity": "high"}]}, ensure_ascii=False)}}]})
        if "分析这张消防检查现场照片" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"caption": "疏散通道堆放杂物", "detected_address": "", "detected_violation": "疏散通道被占用"}, ensure_ascii=False)}}]})
        if "拍照报告" in user_text or "报告级字段" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"title": "某厂房拍照报告", "inspection_unit": "某厂房", "inspection_address": "某市某区某路 2 号", "violation_summary": "疏散通道堆放杂物。"}, ensure_ascii=False)}}]})
        if "询问笔录" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"title": "询问记录", "interviewee_name": "赵某", "interviewer_names": ["张三"], "location": "会议室", "questions_and_answers": [{"question": "情况?", "answer": "安全出口被锁闭"}]}, ensure_ascii=False)}}]})
        if "检索到的材料" in user_text or "法规问答" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": "根据《中华人民共和国消防法》第二十八条,任何单位、个人不得锁闭、封堵安全出口。"}}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "画面分析摘要。"}}]})
    if path.endswith("/embeddings"):
        body = json.loads(request.content)
        inputs = body.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        return httpx.Response(200, json={"data": [{"index": i, "embedding": [0.1 * (i + 1) + 0.01 * j for j in range(8)]} for i in range(len(inputs))]})
    if path.endswith("/audio/transcriptions"):
        return httpx.Response(200, json={"text": "现场负责人承认安全出口被锁闭。"})
    if path.endswith("/rerank"):
        body = json.loads(request.content)
        n = len(body.get("documents", []))
        return httpx.Response(200, json={"results": [{"index": i, "relevance_score": 1.0 - i * 0.1} for i in range(n)]})
    return httpx.Response(404, json={"error": "not found"})


@pytest.fixture()
def fake_ai(monkeypatch):
    import importlib

    from app.services.ai import client as client_mod
    from app.core.config import get_settings

    transport = httpx.MockTransport(_ai_transport_handler)

    class FakeClient(client_mod.AIProviderClient):
        def __init__(self, *args, **kwargs):
            self.settings = get_settings()
            self.base_url = "https://fake.test/v1"
            self.api_key = "fake-key"
            self.timeout = 30
            self._transport = transport

        def _client(self):
            return httpx.Client(
                base_url=self.base_url,
                headers={"Authorization": "Bearer fake"},
                timeout=self.timeout,
                transport=self._transport,
            )

    for mod_name in ["client", "llm", "vision", "ocr", "speech", "embedding", "reranker"]:
        mod = importlib.import_module(f"app.services.ai.{mod_name}")
        monkeypatch.setattr(mod, "AIProviderClient", FakeClient)

    monkeypatch.setattr(get_settings(), "OPENAI_API_KEY", "fake-key")
    from app.services.aiplatform.router import resolve_model

    resolve_model.cache_clear()
    monkeypatch.setattr(get_settings(), "LLM_MODEL", "fake-llm")
    monkeypatch.setattr(get_settings(), "VISION_MODEL", "fake-vision")
    monkeypatch.setattr(get_settings(), "OCR_MODEL", "fake-ocr")
    monkeypatch.setattr(get_settings(), "SPEECH_MODEL", "fake-speech")
    monkeypatch.setattr(get_settings(), "EMBEDDING_MODEL", "fake-embedding")
    monkeypatch.setattr(get_settings(), "RERANK_MODEL", "fake-rerank")
    return transport

