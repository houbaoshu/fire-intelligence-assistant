"""Prompt catalog service: versioned, admin-editable prompts.

Seeded from app/prompts/*.py constants; prompts are resolved through this
service so business code never hard-codes prompt text.
"""
from __future__ import annotations

import importlib
import inspect
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.aiplatform import PromptVersion


@dataclass
class PromptEntry:
    key: str
    name: str
    description: str
    content: str


def _seed_catalog() -> list[PromptEntry]:
    entries: list[PromptEntry] = []
    modules = ["qa", "inspection", "photo_report", "interview"]
    for mod_name in modules:
        mod = importlib.import_module(f"app.prompts.{mod_name}")
        for name, value in vars(mod).items():
            if name.startswith("_") or not isinstance(value, str) or len(value) < 20:
                continue
            entries.append(
                PromptEntry(
                    key=f"{mod_name}.{name}",
                    name=name,
                    description=f"来自 app/prompts/{mod_name}.py 的 {name}",
                    content=value,
                )
            )
    return entries


class PromptService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_seeded(self) -> None:
        """Idempotently seed the catalog from the code constants."""
        for entry in _seed_catalog():
            exists = self.db.scalar(select(PromptVersion).where(PromptVersion.key == entry.key))
            if exists is None:
                self.db.add(
                    PromptVersion(
                        key=entry.key,
                        name=entry.name,
                        description=entry.description,
                        content=entry.content,
                        version=1,
                        is_active=True,
                    )
                )
        self.db.flush()

    def list(self, *, page: int = 1, page_size: int = 50) -> tuple[list[PromptVersion], int]:
        from sqlalchemy import func

        total = int(self.db.scalar(select(func.count(PromptVersion.id))) or 0)
        items = list(
            self.db.scalars(
                select(PromptVersion)
                .order_by(PromptVersion.key)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return items, total

    def get_active(self, key: str) -> str:
        prompt = self.db.scalar(
            select(PromptVersion).where(PromptVersion.key == key, PromptVersion.is_active.is_(True))
        )
        if prompt is None:
            raise NotFoundError(f"Prompt 不存在:{key}")
        return prompt.content

    def update(self, actor, prompt_id: uuid.UUID | str, *, content: str) -> PromptVersion:
        prompt = self.db.get(PromptVersion, uuid.UUID(str(prompt_id)))
        if prompt is None:
            raise NotFoundError("Prompt 不存在")
        if not content.strip():
            raise ValidationError("Prompt 内容不能为空")
        # versioned update: bump version, keep history, activate the new one
        prompt.is_active = False
        new_version = PromptVersion(
            key=prompt.key,
            name=prompt.name,
            description=prompt.description,
            content=content,
            version=prompt.version + 1,
            is_active=True,
            created_by=getattr(actor, "id", None),
        )
        self.db.add(new_version)
        self.db.commit()
        return new_version
