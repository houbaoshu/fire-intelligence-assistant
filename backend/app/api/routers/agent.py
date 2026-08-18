"""Agent 路由（API.md §12.5，M8）。

同步有界执行（AGENT_MAX_STEPS / AGENT_MAX_SUBTASKS / AGENT_TIMEOUT_SECONDS）；
LLM 未配置时由模型路由抛出可读 AI_SERVICE_NOT_CONFIGURED 错误。
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import DbSession, require_permission
from app.core.config import get_settings
from app.models.user import User
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.services.ai.agent import AgentOrchestrator, builtin_tools, load_mcp_tools
from app.services.ai.llm import LLMService

router = APIRouter(prefix="/agent", tags=["agent"])

AgentRun = Depends(require_permission("agent.run"))


@router.post("/run", response_model=AgentRunResponse)
def run_agent(
    payload: AgentRunRequest,
    session: DbSession,
    current_user: User = AgentRun,
) -> AgentRunResponse:
    settings = get_settings()
    tools = builtin_tools(session, current_user) + load_mcp_tools(settings)
    orchestrator = AgentOrchestrator(
        LLMService(session=session),
        tools,
        max_steps=settings.AGENT_MAX_STEPS,
        max_subtasks=settings.AGENT_MAX_SUBTASKS,
        timeout_seconds=settings.AGENT_TIMEOUT_SECONDS,
    )
    result = orchestrator.run(payload.goal)
    return AgentRunResponse(
        answer=result.answer, steps=result.steps, tools_used=result.tools_used
    )
