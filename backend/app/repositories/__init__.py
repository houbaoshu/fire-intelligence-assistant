"""Repository layer: encapsulate database access.

Business rules must NOT live in repositories (see ARCHITECTURE.md §7.3).
"""
from .base import BaseRepository

__all__ = ["BaseRepository"]
