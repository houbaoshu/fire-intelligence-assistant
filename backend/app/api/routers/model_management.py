"""Model configuration management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role
from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.models.model_config import ModelConfiguration
from app.models.user import User
from app.schemas.model_config import (
    ModelConfigurationCreate,
    ModelConfigurationResponse,
    ModelConfigurationUpdate,
)

logger = get_logger(__name__)

router = APIRouter(tags=["model-management"])


@router.get(
    "",
    response_model=list[ModelConfigurationResponse],
    status_code=status.HTTP_200_OK,
    summary="List model configurations",
)
async def list_models(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[ModelConfigurationResponse]:
    """Return all model configurations. Admin only."""
    stmt = select(ModelConfiguration).order_by(ModelConfiguration.created_at.desc())
    result = await db.execute(stmt)
    configs = result.scalars().all()
    return [ModelConfigurationResponse.model_validate(c) for c in configs]


@router.post(
    "",
    response_model=ModelConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a model configuration",
)
async def create_model(
    body: ModelConfigurationCreate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> ModelConfigurationResponse:
    """Create a new model configuration. Admin only."""
    config = ModelConfiguration(
        name=body.name,
        provider=body.provider,
        model_name=body.model_name,
        config=body.config,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)

    logger.info(
        "Model configuration created: %s (id=%s) by user %s",
        config.name,
        config.id,
        current_user.id,
    )
    return ModelConfigurationResponse.model_validate(config)


@router.put(
    "/{config_id}",
    response_model=ModelConfigurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a model configuration",
)
async def update_model(
    config_id: str,
    body: ModelConfigurationUpdate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> ModelConfigurationResponse:
    """Update an existing model configuration. Admin only."""
    stmt = select(ModelConfiguration).where(ModelConfiguration.id == config_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config is None:
        raise NotFoundException(f"Model configuration '{config_id}' not found")

    if body.name is not None:
        config.name = body.name
    if body.provider is not None:
        config.provider = body.provider
    if body.model_name is not None:
        config.model_name = body.model_name
    if body.config is not None:
        config.config = body.config
    if body.is_active is not None:
        config.is_active = body.is_active

    await db.flush()
    await db.refresh(config)

    logger.info(
        "Model configuration updated: %s by user %s",
        config_id,
        current_user.id,
    )
    return ModelConfigurationResponse.model_validate(config)
