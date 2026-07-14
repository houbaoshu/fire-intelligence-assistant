from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class StoredObject:
    path: str
    size_bytes: int


class StorageProvider(Protocol):
    def initialize(self) -> None: ...

    def save(self, *, category: str, filename: str, source: BinaryIO) -> StoredObject: ...

    def open(self, path: str) -> BinaryIO: ...

    def delete(self, path: str) -> None: ...

    def exists(self, path: str) -> bool: ...

    def resolve(self, path: str) -> Path: ...
