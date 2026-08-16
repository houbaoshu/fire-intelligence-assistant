"""AI Platform endpoints (Milestone 8).

Prompt catalog, model configurations, evaluations, plugins, agents and MCP.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.dependencies import CurrentUser, DB
from app.core.exceptions import ForbiddenError
from app.mcp.client import configured_servers
from app.services.ai.agent import AgentOrchestrator
from app.services.aiplatform.evaluation_service import EvaluationService
from app.services.aiplatform.model_service import ModelService
from app.services.aiplatform.plugin_service import PluginService
from app.services.aiplatform.prompt_service import PromptService

router = APIRouter(prefix="/ai-platform", tags=["ai-platform"])


def _require_admin(user) -> None:
    if user.role != "admin":
        raise ForbiddenError("仅管理员可管理 AI 平台配置")


class PromptUpdate(BaseModel):
    content: str = Field(min_length=1)


class ModelCreate(BaseModel):
    name: str
    kind: str
    model_name: str
    provider: str = "openai-compatible"
    base_url: str | None = None
    api_key_ref: str | None = None
    priority: int = 0


class EvalRun(BaseModel):
    name: str
    questions: list[str] = Field(min_length=1)


class AgentQuery(BaseModel):
    task: str = Field(min_length=1, max_length=2000)


@router.get("/prompts")
def list_prompts(user: CurrentUser, db: DB, page: int = 1, page_size: int = 100):
    items, total = PromptService(db).list(page=page, page_size=page_size)
    return {
        "items": [
            {
                "id": str(p.id),
                "key": p.key,
                "name": p.name,
                "description": p.description,
                "version": p.version,
                "is_active": p.is_active,
                "updated_at": p.updated_at,
            }
            for p in items
        ],
        "total": total,
    }


@router.get("/prompts/{prompt_id}")
def get_prompt(user: CurrentUser, db: DB, prompt_id: uuid.UUID):
    from app.core.exceptions import NotFoundError

    from app.models.aiplatform import PromptVersion

    p = db.get(PromptVersion, prompt_id)
    if p is None:
        raise NotFoundError("Prompt 不存在")
    return {
        "id": str(p.id),
        "key": p.key,
        "name": p.name,
        "description": p.description,
        "content": p.content,
        "version": p.version,
        "is_active": p.is_active,
        "updated_at": p.updated_at,
    }


@router.put("/prompts/{prompt_id}")
def update_prompt(user: CurrentUser, db: DB, prompt_id: uuid.UUID, payload: PromptUpdate):
    _require_admin(user)
    p = PromptService(db).update(user, prompt_id, content=payload.content)
    return {"id": str(p.id), "key": p.key, "version": p.version, "is_active": p.is_active}


@router.get("/models")
def list_models(user: CurrentUser, db: DB, kind: str | None = None):
    items = ModelService(db).list(kind)
    return {
        "items": [
            {
                "id": str(m.id),
                "name": m.name,
                "kind": m.kind,
                "provider": m.provider,
                "model_name": m.model_name,
                "base_url": m.base_url,
                "api_key_ref": m.api_key_ref,
                "is_active": m.is_active,
                "priority": m.priority,
            }
            for m in items
        ]
    }


@router.post("/models", status_code=201)
def create_model(user: CurrentUser, db: DB, payload: ModelCreate):
    _require_admin(user)
    m = ModelService(db).create(
        user, name=payload.name, kind=payload.kind, model_name=payload.model_name,
        provider=payload.provider, base_url=payload.base_url,
        api_key_ref=payload.api_key_ref, priority=payload.priority,
    )
    return {"id": str(m.id), "kind": m.kind, "name": m.name}


@router.post("/models/{config_id}/activate")
def activate_model(user: CurrentUser, db: DB, config_id: uuid.UUID):
    _require_admin(user)
    m = ModelService(db).set_active(user, config_id)
    return {"id": str(m.id), "kind": m.kind, "is_active": m.is_active}


@router.delete("/models/{config_id}")
def delete_model(user: CurrentUser, db: DB, config_id: uuid.UUID):
    _require_admin(user)
    ModelService(db).delete(user, config_id)
    return {"deleted": True}


@router.post("/evaluations/run")
def run_evaluation(user: CurrentUser, db: DB, payload: EvalRun):
    _require_admin(user)
    result = EvaluationService(db).run(user, name=payload.name, questions=payload.questions)
    return {
        "id": str(result.id),
        "name": result.name,
        "status": result.status,
        "total_questions": result.total_questions,
        "passed": result.passed,
        "details": result.details,
    }


@router.get("/evaluations")
def list_evaluations(user: CurrentUser, db: DB):
    items = EvaluationService(db).list()
    return {
        "items": [
            {
                "id": str(e.id),
                "name": e.name,
                "status": e.status,
                "total_questions": e.total_questions,
                "passed": e.passed,
                "created_at": e.created_at,
            }
            for e in items
        ]
    }


@router.get("/plugins")
def list_plugins(user: CurrentUser, db: DB):
    svc = PluginService(db)
    svc.sync_records()
    return {
        "items": [
            {"id": str(p.id), "name": p.name, "version": p.version, "description": p.description, "enabled": p.enabled}
            for p in svc.list()
        ]
    }


@router.post("/agents/run")
def run_agent(user: CurrentUser, db: DB, payload: AgentQuery):
    result = AgentOrchestrator(db, user).run(payload.task)
    return result


@router.get("/mcp/servers")
def list_mcp_servers(user: CurrentUser, db: DB):
    servers = configured_servers()
    return {
        "items": [
            {
                "name": s.name,
                "url": s.url,
                "tools": [t.name for t in s.list_tools()],
            }
            for s in servers
        ]
    }
