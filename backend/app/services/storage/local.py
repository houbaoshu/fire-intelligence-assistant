from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.services.storage.protocol import StoredObject

SAFE_CATEGORY = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class LocalStorageProvider:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for category in ("uploads", "temporary", "knowledge", "generated", "key-frames"):
            (self.root / category).mkdir(exist_ok=True)

    def save(self, *, category: str, filename: str, source: BinaryIO) -> StoredObject:
        if not SAFE_CATEGORY.fullmatch(category):
            raise ValueError("Invalid storage category")
        safe_name = Path(filename).name
        suffix = Path(safe_name).suffix.lower()[:16]
        relative = Path(category) / f"{uuid.uuid4().hex}{suffix}"
        destination = self.resolve(relative.as_posix())
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output:
            shutil.copyfileobj(source, output)
        return StoredObject(path=relative.as_posix(), size_bytes=destination.stat().st_size)

    def open(self, path: str) -> BinaryIO:
        return self.resolve(path).open("rb")

    def delete(self, path: str) -> None:
        self.resolve(path).unlink(missing_ok=True)

    def exists(self, path: str) -> bool:
        return self.resolve(path).is_file()

    def resolve(self, path: str) -> Path:
        candidate = (self.root / path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("Storage path escapes the configured root")
        return candidate
