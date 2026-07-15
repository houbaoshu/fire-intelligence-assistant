"""Service for managing prompt templates."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.models.prompt import PromptVersion
from app.models.user import User
from app.schemas.prompt import PromptVersionCreate

logger = get_logger(__name__)


class PromptService:
    """Manage prompt templates and their versions."""

    @staticmethod
    async def get_active_prompt(name: str, db: AsyncSession) -> PromptVersion | None:
        """Return the active prompt version for a given name, or None."""
        stmt = (
            select(PromptVersion)
            .where(
                PromptVersion.name == name,
                PromptVersion.is_active.is_(True),
            )
            .order_by(PromptVersion.version.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_prompt_version(
        data: PromptVersionCreate, user: User, db: AsyncSession
    ) -> PromptVersion:
        """Create a new prompt version.

        Automatically increments the version number and deactivates
        any previously active version with the same name.
        """
        # Find the current max version for this prompt name
        stmt = (
            select(PromptVersion.version)
            .where(PromptVersion.name == data.name)
            .order_by(PromptVersion.version.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        max_version = result.scalar_one_or_none()
        new_version = (max_version or 0) + 1

        # Deactivate existing active versions
        deactivate_stmt = select(PromptVersion).where(
            PromptVersion.name == data.name,
            PromptVersion.is_active.is_(True),
        )
        deactivate_result = await db.execute(deactivate_stmt)
        for existing in deactivate_result.scalars().all():
            existing.is_active = False

        # Create new version
        prompt = PromptVersion(
            name=data.name,
            version=new_version,
            template=data.template,
            variables=data.variables,
            description=data.description,
            is_active=True,
            created_by=user.id,
        )
        db.add(prompt)
        await db.flush()
        await db.refresh(prompt)

        logger.info(
            "Prompt version created: %s v%d (id=%s) by user %s",
            data.name,
            new_version,
            prompt.id,
            user.id,
        )
        return prompt

    @staticmethod
    async def list_prompts(db: AsyncSession) -> list[PromptVersion]:
        """Return all prompt versions, ordered by name and version."""
        stmt = select(PromptVersion).order_by(
            PromptVersion.name.asc(), PromptVersion.version.desc()
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def render_prompt(name: str, variables: dict[str, str], db: AsyncSession) -> str:
        """Get the active prompt template and render it with the provided variables.

        Raises ``NotFoundException`` if no active prompt is found for the given name.
        """
        prompt = await PromptService.get_active_prompt(name, db)
        if prompt is None:
            raise NotFoundException(f"No active prompt found with name '{name}'")

        try:
            rendered = prompt.template.format(**variables)
        except KeyError as exc:
            raise NotFoundException(
                f"Prompt '{name}' requires variable '{exc.args[0]}' which was not provided"
            ) from exc

        return rendered
