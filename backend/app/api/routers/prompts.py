"""Prompt management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.prompt import (
    PromptRenderRequest,
    PromptRenderResponse,
    PromptVersionCreate,
    PromptVersionResponse,
)
from app.services.prompt_service import PromptService

logger = get_logger(__name__)

router = APIRouter(tags=["prompts"])


@router.get(
    "",
    response_model=list[PromptVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="List all prompt versions",
)
async def list_prompts(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[PromptVersionResponse]:
    """Return all prompt versions. Admin only."""
    prompts = await PromptService.list_prompts(db)
    return [PromptVersionResponse.model_validate(p) for p in prompts]


@router.post(
    "",
    response_model=PromptVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new prompt version",
)
async def create_prompt(
    body: PromptVersionCreate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> PromptVersionResponse:
    """Create a new prompt version. Admin only.

    Automatically increments the version number and deactivates
    any previously active version with the same name.
    """
    prompt = await PromptService.create_prompt_version(body, current_user, db)
    return PromptVersionResponse.model_validate(prompt)


@router.get(
    "/{name}",
    response_model=PromptVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active version of a prompt",
)
async def get_prompt(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PromptVersionResponse:
    """Return the active version of a prompt by name."""
    prompt = await PromptService.get_active_prompt(name, db)
    if prompt is None:
        raise NotFoundException(f"No active prompt found with name '{name}'")
    return PromptVersionResponse.model_validate(prompt)


@router.post(
    "/{name}/render",
    response_model=PromptRenderResponse,
    status_code=status.HTTP_200_OK,
    summary="Render a prompt with variables",
)
async def render_prompt(
    name: str,
    body: PromptRenderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PromptRenderResponse:
    """Render a prompt template with the provided variables."""
    prompt = await PromptService.get_active_prompt(name, db)
    if prompt is None:
        raise NotFoundException(f"No active prompt found with name '{name}'")

    rendered = await PromptService.render_prompt(name, body.variables, db)
    return PromptRenderResponse(
        name=name,
        version=prompt.version,
        rendered=rendered,
    )
