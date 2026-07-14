from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.permissions import require_admin
from app.db.models import (
    AIModelConfig,
    EvaluationRun,
    PluginRegistration,
    PromptTemplate,
    User,
    WorkflowDefinition,
)
from app.db.session import get_db
from app.schemas.business import PlatformResourceCreate
from app.services.audit import add_audit_log

router = APIRouter(prefix="/platform", tags=["ai-platform"])
RESOURCE_MODELS: dict[str, type[Any]] = {
    "models": AIModelConfig,
    "prompts": PromptTemplate,
    "workflows": WorkflowDefinition,
    "plugins": PluginRegistration,
    "evaluations": EvaluationRun,
}
SENSITIVE_WORDS = frozenset({"secret", "password", "token", "api_key", "apikey", "credential"})


def _safe_configuration(value: object) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if any(word in key.lower() for word in SENSITIVE_WORDS):
                raise AppError(
                    status_code=422,
                    code="SECRET_CONFIGURATION_FORBIDDEN",
                    message="Secrets must be supplied through the deployment secret manager.",
                )
            _safe_configuration(nested)
    elif isinstance(value, list):
        for nested in value:
            _safe_configuration(nested)


def _serialize(value: object) -> dict[str, object]:
    return {
        column.name: getattr(value, column.name)
        for column in value.__table__.columns  # type: ignore[attr-defined]
    }


@router.get("/{resource}")
def list_resources(
    resource: str,
    session: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[dict[str, object]]:
    model = RESOURCE_MODELS.get(resource)
    if model is None:
        raise AppError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found.")
    return [_serialize(item) for item in session.scalars(select(model))]


@router.post("/{resource}", status_code=201)
def create_resource(
    resource: str,
    payload: PlatformResourceCreate,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict[str, object]:
    model = RESOURCE_MODELS.get(resource)
    if model is None:
        raise AppError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found.")
    _safe_configuration(payload.data)
    allowed = {column.name for column in model.__table__.columns} - {
        "id",
        "created_at",
        "updated_at",
    }
    values = {key: value for key, value in payload.data.items() if key in allowed}
    if "created_by" in allowed:
        values["created_by"] = user.id
    try:
        item = model(**values)
        session.add(item)
        session.flush()
    except TypeError as error:
        raise AppError(
            status_code=422,
            code="INVALID_PLATFORM_RESOURCE",
            message="Required platform resource fields are missing or invalid.",
        ) from error
    add_audit_log(
        session,
        user_id=user.id,
        action=f"platform.{resource}.create",
        entity_type=resource,
        entity_id=item.id,
        request_id=getattr(request.state, "request_id", None),
    )
    session.commit()
    return _serialize(item)


@router.delete("/{resource}/{resource_id}", status_code=204)
def delete_resource(
    resource: str,
    resource_id: uuid.UUID,
    session: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    model = RESOURCE_MODELS.get(resource)
    item = session.get(model, resource_id) if model else None
    if item is None:
        raise AppError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found.")
    session.delete(item)
    session.commit()
