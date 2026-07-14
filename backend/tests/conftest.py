from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
        storage_root=tmp_path / "storage",
        auth_secret_key=SecretStr("test-signing-key-that-is-long-enough-for-tests"),
        cors_origins=["http://testserver"],
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(app.state.engine)
