from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from app.services.storage import LocalStorageProvider


def test_local_storage_uses_safe_generated_paths(tmp_path: Path) -> None:
    storage = LocalStorageProvider(tmp_path / "objects")
    storage.initialize()
    stored = storage.save(
        category="uploads", filename="../../inspection.MP4", source=BytesIO(b"video")
    )
    assert stored.path.startswith("uploads/")
    assert stored.path.endswith(".mp4")
    assert stored.size_bytes == 5
    assert storage.open(stored.path).read() == b"video"


def test_local_storage_rejects_path_traversal(tmp_path: Path) -> None:
    storage = LocalStorageProvider(tmp_path / "objects")
    storage.initialize()
    with pytest.raises(ValueError):
        storage.resolve("../outside")
