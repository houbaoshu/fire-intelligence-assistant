"""AI 平台管理路由（API.md §12，M8）。保持薄：解析请求、调用服务。

按权限码授权：admin.prompts / admin.models / admin.evaluations / admin.plugins。
"""

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import DbSession, require_permission
from app.models.user import User
from app.schemas.admin import DeleteResponse
from app.schemas.ai_platform import (
    EvaluationDetailResponse,
    EvaluationResultItem,
    EvaluationRunRequest,
    ModelConfigCreateRequest,
    ModelConfigItem,
    ModelConfigListResponse,
    ModelConfigUpdateRequest,
    PluginItem,
    PluginListResponse,
    PluginUpdateRequest,
    PromptActivateResponse,
    PromptVersionCreateRequest,
    PromptVersionItem,
    PromptVersionListResponse,
)
from app.schemas.common import Page
from app.services.evaluation_service import EvaluationService
from app.services.model_config_service import ModelConfigService
from app.services.plugin_service import PluginService
from app.services.prompt_service import PromptService

router = APIRouter(prefix="/admin", tags=["ai-platform"])

PromptsAdmin = Depends(require_permission("admin.prompts"))
ModelsAdmin = Depends(require_permission("admin.models"))
EvaluationsAdmin = Depends(require_permission("admin.evaluations"))
PluginsAdmin = Depends(require_permission("admin.plugins"))


def _to_prompt_item(row) -> PromptVersionItem:
    return PromptVersionItem(
        id=row.id,
        key=row.key,
        name=row.name,
        description=row.description,
        content=row.content,
        version=row.version,
        is_active=row.is_active,
        created_at=row.created_at,
    )


def _to_model_item(row) -> ModelConfigItem:
    return ModelConfigItem(
        id=row.id,
        name=row.name,
        kind=row.kind,
        provider=row.provider,
        model_name=row.model_name,
        base_url=row.base_url,
        api_key_ref=row.api_key_ref,
        is_active=row.is_active,
        priority=row.priority,
    )


def _to_evaluation_item(row) -> EvaluationResultItem:
    return EvaluationResultItem(
        id=row.id,
        name=row.name,
        status=row.status,
        total_questions=row.total_questions,
        passed=row.passed,
        created_at=row.created_at,
    )


def _to_plugin_item(row) -> PluginItem:
    return PluginItem(
        id=row.id,
        name=row.name,
        version=row.version,
        description=row.description,
        entry_point=row.entry_point,
        enabled=row.enabled,
    )


# ---------- Prompt 管理（§12.1） ----------


@router.get("/prompts", response_model=PromptVersionListResponse)
def list_prompts(
    session: DbSession, current_user: User = PromptsAdmin
) -> PromptVersionListResponse:
    rows = PromptService(session).list_versions()
    return PromptVersionListResponse(items=[_to_prompt_item(r) for r in rows])


@router.post("/prompts/{key}/versions", response_model=PromptVersionItem)
def create_prompt_version(
    key: str,
    payload: PromptVersionCreateRequest,
    session: DbSession,
    current_user: User = PromptsAdmin,
) -> PromptVersionItem:
    row = PromptService(session).create_version(
        key,
        content=payload.content,
        name=payload.name,
        description=payload.description,
        created_by=current_user.id,
    )
    return _to_prompt_item(row)


@router.post("/prompts/{prompt_id}/activate", response_model=PromptActivateResponse)
def activate_prompt(
    prompt_id: uuid.UUID,
    session: DbSession,
    current_user: User = PromptsAdmin,
) -> PromptActivateResponse:
    row = PromptService(session).activate(prompt_id)
    return PromptActivateResponse(id=row.id, is_active=row.is_active)


# ---------- 模型管理（§12.2） ----------


@router.get("/models", response_model=ModelConfigListResponse)
def list_models(
    session: DbSession, current_user: User = ModelsAdmin
) -> ModelConfigListResponse:
    rows = ModelConfigService(session).list()
    return ModelConfigListResponse(items=[_to_model_item(r) for r in rows])


@router.post("/models", response_model=ModelConfigItem)
def create_model(
    payload: ModelConfigCreateRequest,
    session: DbSession,
    current_user: User = ModelsAdmin,
) -> ModelConfigItem:
    return _to_model_item(ModelConfigService(session).create(payload))


@router.put("/models/{config_id}", response_model=ModelConfigItem)
def update_model(
    config_id: uuid.UUID,
    payload: ModelConfigUpdateRequest,
    session: DbSession,
    current_user: User = ModelsAdmin,
) -> ModelConfigItem:
    return _to_model_item(ModelConfigService(session).update(config_id, payload))


@router.delete("/models/{config_id}", response_model=DeleteResponse)
def delete_model(
    config_id: uuid.UUID,
    session: DbSession,
    current_user: User = ModelsAdmin,
) -> DeleteResponse:
    row = ModelConfigService(session).delete(config_id)
    return DeleteResponse(id=row.id, deleted=True)


# ---------- 评估（§12.3） ----------


@router.post("/evaluations", response_model=EvaluationDetailResponse)
def run_evaluation(
    payload: EvaluationRunRequest,
    session: DbSession,
    current_user: User = EvaluationsAdmin,
) -> EvaluationDetailResponse:
    row = EvaluationService(session).run(payload.name, payload.questions, current_user.id)
    return EvaluationDetailResponse(
        **_to_evaluation_item(row).model_dump(), details=row.details
    )


@router.get("/evaluations", response_model=Page[EvaluationResultItem])
def list_evaluations(
    session: DbSession,
    current_user: User = EvaluationsAdmin,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[EvaluationResultItem]:
    rows, total = EvaluationService(session).list(page, page_size)
    return Page(
        items=[_to_evaluation_item(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationDetailResponse)
def get_evaluation(
    evaluation_id: uuid.UUID,
    session: DbSession,
    current_user: User = EvaluationsAdmin,
) -> EvaluationDetailResponse:
    row = EvaluationService(session).get(evaluation_id)
    return EvaluationDetailResponse(
        **_to_evaluation_item(row).model_dump(), details=row.details
    )


# ---------- 插件（§12.4） ----------


@router.get("/plugins", response_model=PluginListResponse)
def list_plugins(
    session: DbSession, current_user: User = PluginsAdmin
) -> PluginListResponse:
    rows = PluginService(session).list()
    return PluginListResponse(items=[_to_plugin_item(r) for r in rows])


@router.put("/plugins/{plugin_id}", response_model=PluginItem)
def update_plugin(
    plugin_id: uuid.UUID,
    payload: PluginUpdateRequest,
    session: DbSession,
    current_user: User = PluginsAdmin,
) -> PluginItem:
    return _to_plugin_item(PluginService(session).set_enabled(plugin_id, payload.enabled))
