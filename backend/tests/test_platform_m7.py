"""M7 平台工程化测试：/metrics、TTL 缓存、默认管理员种子、备份脚本、S3 存储。"""

import os
import re
import sqlite3
import subprocess
from pathlib import Path

from app.core.bootstrap import seed_default_admin
from app.core.cache import TTLCache, get_cache
from app.core.config import get_settings
from app.db import SessionLocal
from app.models.user import User
from app.services.storage import S3StorageProvider

from .helpers import auth_headers, generate_inspection, register, wait_task

BACKEND_DIR = Path(__file__).resolve().parent.parent


# ---------- /metrics ----------


def test_metrics_endpoint_format_and_growth(client):
    before = client.get("/metrics")
    assert before.status_code == 200
    assert before.headers["content-type"].startswith("text/plain")
    text = before.text
    assert "# HELP http_requests_total" in text
    assert "# TYPE http_request_duration_seconds histogram" in text
    assert "# TYPE ai_tasks_terminal_total counter" in text

    def health_count(body: str) -> int:
        m = re.search(
            r'^http_requests_total\{[^}]*route="/health"[^}]*\} (\d+)$',
            body,
            re.MULTILINE,
        )
        return int(m.group(1)) if m else 0

    base = health_count(text)
    client.get("/health")
    client.get("/health")
    after = client.get("/metrics")
    # 调用若干 API 后计数增长；/metrics 自身不计入
    assert health_count(after.text) == base + 2
    assert 'route="/metrics"' not in after.text


def test_metrics_task_terminal_counter(client):
    tokens = register(client)
    before = client.get("/metrics").text
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)  # AI 未配置时按预期 failed
    after = client.get("/metrics").text
    pattern = (
        r'^ai_tasks_terminal_total\{status="failed",'
        r'task_type="inspection_record_generation"\} (\d+)$'
    )
    b = re.search(pattern, before, re.MULTILINE)
    a = re.search(pattern, after, re.MULTILINE)
    assert a is not None
    assert int(a.group(1)) == (int(b.group(1)) if b else 0) + 1


# ---------- TTL 缓存 ----------


def test_ttl_cache_unit():
    cache = TTLCache()
    cache.set("k1", "v1", ttl_seconds=60)
    assert cache.get("k1") == "v1"
    cache.set("k2", "v2", ttl_seconds=-1)  # 立即过期
    assert cache.get("k2") is None
    cache.set("prefix:a", 1, ttl_seconds=60)
    cache.set("prefix:b", 2, ttl_seconds=60)
    cache.set("other", 3, ttl_seconds=60)
    assert cache.invalidate_prefix("prefix:") == 2
    assert cache.get("prefix:a") is None
    assert cache.get("other") == 3


def test_statistics_cache_hit_and_invalidation(client):
    from app.schemas.statistics import StatisticsResponse

    get_cache().clear()
    tokens = register(client)
    resp1 = client.get("/api/statistics", headers=auth_headers(tokens))
    assert resp1.status_code == 200
    key = f"statistics:{tokens['user']['id']}"
    cached = get_cache().get(key)
    assert isinstance(cached, StatisticsResponse)  # 第一次调用后已缓存

    # 命中缓存：generated_at 与首次一致（TTL 内不重算）
    resp2 = client.get("/api/statistics", headers=auth_headers(tokens))
    assert resp2.json()["generated_at"] == resp1.json()["generated_at"]

    # 记录变更后缓存按前缀失效：新建任务（提交即失效）→ generated_at 刷新
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)
    assert get_cache().get(key) is None
    resp3 = client.get("/api/statistics", headers=auth_headers(tokens))
    assert resp3.json()["generated_at"] != resp1.json()["generated_at"]


def test_knowledge_status_cached(client):
    get_cache().clear()
    tokens = register(client)
    resp = client.get("/api/knowledge/status", headers=auth_headers(tokens))
    assert resp.status_code == 200
    assert get_cache().get("knowledge:status") == resp.json()


# ---------- 默认管理员种子 ----------


def test_seed_default_admin_idempotent(monkeypatch):
    monkeypatch.setenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "admin-pass-123")
    get_settings.cache_clear()
    try:
        with SessionLocal() as session:
            assert seed_default_admin(session) is True
            users = session.query(User).filter_by(email="admin@example.com").all()
            assert len(users) == 1
            assert users[0].role == "admin"
            assert users[0].password_hash != "admin-pass-123"
            # 幂等：再次调用不重复创建
            assert seed_default_admin(session) is False
            assert session.query(User).filter_by(email="admin@example.com").count() == 1
    finally:
        get_settings.cache_clear()


def test_seed_default_admin_skipped_when_unset(monkeypatch):
    monkeypatch.delenv("DEFAULT_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("DEFAULT_ADMIN_PASSWORD", raising=False)
    get_settings.cache_clear()
    try:
        with SessionLocal() as session:
            assert seed_default_admin(session) is False
    finally:
        get_settings.cache_clear()


# ---------- 备份脚本 ----------


def test_backup_script_syntax():
    proc = subprocess.run(
        ["bash", "-n", str(BACKEND_DIR / "scripts" / "backup.sh")],
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr.decode()


def test_backup_script_sqlite_run(tmp_path):
    db_path = tmp_path / "app.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()
    storage = tmp_path / "storage"
    (storage / "a").mkdir(parents=True)
    (storage / "a" / "f.txt").write_text("hello")
    vectorstore = tmp_path / "vectorstore"
    vectorstore.mkdir()
    (vectorstore / "index.bin").write_bytes(b"vec")

    out_dir = tmp_path / "backups"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "STORAGE_DIR": str(storage),
        "VECTOR_STORE_DIR": str(vectorstore),
        "VECTOR_STORE_PROVIDER": "local",
    }
    proc = subprocess.run(
        ["bash", str(BACKEND_DIR / "scripts" / "backup.sh"), str(out_dir)],
        capture_output=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    backups = list(out_dir.glob("backup-*"))
    assert len(backups) == 1
    backup = backups[0]
    assert (backup / "db.sqlite3").exists()
    assert (backup / "storage.tar.gz").exists()
    assert (backup / "vectorstore.tar.gz").exists()
    # 快照数据一致
    check = sqlite3.connect(backup / "db.sqlite3")
    assert check.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    check.close()


def test_backup_script_postgres_without_pg_dump_errors(tmp_path):
    env = {
        "PATH": "/usr/bin:/bin",  # 假定该 PATH 下无 pg_dump；若有则跳过语义由断言保证
        "DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/db",
    }
    import shutil

    if shutil.which("pg_dump", path=env["PATH"]):
        import pytest

        pytest.skip("环境存在 pg_dump，跳过缺失报错路径")
    proc = subprocess.run(
        ["bash", str(BACKEND_DIR / "scripts" / "backup.sh"), str(tmp_path / "out")],
        capture_output=True,
        env=env,
    )
    assert proc.returncode != 0
    assert "pg_dump" in proc.stderr.decode()


# ---------- S3 存储（stub 客户端） ----------


class _StubS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, Bucket, Key, Body):
        assert Bucket == "test-bucket"
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        import io

        if Key not in self.objects:
            raise FileNotFoundError(Key)
        return {"Body": io.BytesIO(self.objects[Key])}

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FileNotFoundError(Key)


def test_s3_storage_provider_with_stub_client():
    provider = S3StorageProvider(bucket="test-bucket", client=_StubS3Client())
    key = "uploads/2026/test.bin"
    assert provider.save(key, b"data") == key
    assert provider.exists(key)
    assert provider.read(key) == b"data"
    provider.delete(key)
    assert not provider.exists(key)


def test_s3_storage_provider_requires_bucket():
    import pytest

    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="S3_BUCKET"):
            S3StorageProvider(bucket="", client=_StubS3Client())
    finally:
        get_settings.cache_clear()
