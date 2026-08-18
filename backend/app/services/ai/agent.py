"""Agent 与多智能体编排（M8，API.md §12.5）。

- ``Agent``：基于 OpenAI 兼容 function calling 的执行循环，受最大步数
  （AGENT_MAX_STEPS）与总超时（AGENT_TIMEOUT_SECONDS）约束；工具执行失败
  以可读文本回喂模型，不静默吞错。
- 内置工具：``knowledge_search``（走 M3 Retriever 检索）、
  ``statistics_summary``（走 StatisticsService 聚合）；MCP 服务器工具经
  ``load_mcp_tools`` 并入可用工具集。
- ``AgentOrchestrator``：规划器（LLM 拆解目标为子任务）→ 逐个执行
  （每个子任务是带不同工具子集的 Agent 角色）→ 汇总。不引入外部框架。
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.user import User
from app.prompts.agent import build_planner_user_prompt, build_summarizer_user_prompt
from app.services.ai.llm import LLMService
from app.services.prompt_service import get_prompt

logger = get_logger("ai.agent")

_STEP_SUMMARY_CHARS = 200


@dataclass(frozen=True)
class AgentTool:
    """Agent 工具：name 唯一；handler 接收参数 dict，返回文本结果。"""

    name: str
    description: str
    parameters: dict  # JSON Schema（OpenAI function calling parameters）
    handler: Callable[[dict], str]


@dataclass
class AgentResult:
    answer: str
    steps: list[dict] = field(default_factory=list)  # [{tool, summary}]
    tools_used: list[str] = field(default_factory=list)


def _tool_schema(tool: AgentTool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


class Agent:
    """单角色 Agent：固定系统 Prompt + 工具子集的 function-calling 循环。"""

    def __init__(
        self,
        llm: LLMService,
        tools: list[AgentTool],
        *,
        max_steps: int,
        timeout_seconds: float,
        system_prompt: str | None = None,
    ) -> None:
        self._llm = llm
        self._tools = {t.name: t for t in tools}
        self._max_steps = max_steps
        self._timeout = timeout_seconds
        # Prompt 运行时取用（M8）：DB 生效版本优先，回退 app/prompts/agent.py 常量
        self._system_prompt = system_prompt or get_prompt("agent.AGENT_SYSTEM")

    def run(self, task: str) -> AgentResult:
        messages: list[dict] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": task},
        ]
        deadline = time.monotonic() + self._timeout
        steps: list[dict] = []
        tools_used: set[str] = set()
        for _ in range(self._max_steps):
            if time.monotonic() > deadline:
                raise AppException(
                    "AGENT_TIMEOUT", "Agent 执行超时，请缩小目标范围后重试", 504
                )
            message = self._llm.chat_raw(
                messages, tools=[_tool_schema(t) for t in self._tools.values()] or None
            )
            messages.append(_assistant_message(message))
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                content = message.get("content")
                if not isinstance(content, str) or not content.strip():
                    raise AppException(
                        "AI_SERVICE_ERROR", "AI 能力 llm 返回了空内容", 500
                    )
                return AgentResult(
                    answer=content, steps=steps, tools_used=sorted(tools_used)
                )
            for call in tool_calls:
                name, arguments, call_id = _parse_tool_call(call)
                result_text = self._execute(name, arguments)
                messages.append(
                    {"role": "tool", "tool_call_id": call_id, "content": result_text}
                )
                tools_used.add(name)
                steps.append({"tool": name, "summary": result_text[:_STEP_SUMMARY_CHARS]})
        raise AppException(
            "AGENT_STEP_LIMIT",
            f"Agent 达到最大步数（{self._max_steps}）仍未完成，请缩小目标范围后重试",
            504,
        )

    def _execute(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"错误：工具 {name} 不存在，请从可用工具中选择"
        try:
            return tool.handler(arguments)
        except AppException as exc:
            return f"错误：{exc.message}"
        except Exception as exc:
            logger.info("Agent 工具 %s 执行异常: %s", name, type(exc).__name__)
            return f"错误：工具 {name} 执行失败（{type(exc).__name__}）"


def _assistant_message(message: dict) -> dict:
    """清洗 assistant 消息用于回放（仅保留 content 与 tool_calls）。"""
    replay: dict = {"role": "assistant", "content": message.get("content")}
    if message.get("tool_calls"):
        replay["tool_calls"] = message["tool_calls"]
    return replay


def _parse_tool_call(call: dict) -> tuple[str, dict, str]:
    function = call.get("function") or {}
    name = str(function.get("name") or "")
    raw_arguments = function.get("arguments") or "{}"
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    return name, arguments, str(call.get("id") or "")


# ---------- 内置工具与 MCP 工具适配 ----------


def builtin_tools(session: Session, user: User) -> list[AgentTool]:
    """内置工具：知识检索（M3 Retriever）与统计摘要（StatisticsService）。"""

    def knowledge_search(arguments: dict) -> str:
        from app.rag.retrieval import Retriever

        query = str(arguments.get("query") or "").strip()
        if not query:
            return "错误：knowledge_search 需要 query 参数"
        chunks = Retriever(session).retrieve(query)
        if not chunks:
            return "知识库中未检索到相关内容"
        lines = []
        for chunk in chunks:
            meta = chunk.metadata
            label = meta.get("title") or "未命名文档"
            if meta.get("article_number"):
                label += f" {meta['article_number']}"
            lines.append(f"《{label}》：{chunk.content.strip()}")
        return "\n".join(lines)

    def statistics_summary(_: dict) -> str:
        from app.services.statistics_service import StatisticsService

        stats = StatisticsService(session).get(user)
        return json.dumps(stats.model_dump(mode="json"), ensure_ascii=False)

    return [
        AgentTool(
            name="knowledge_search",
            description="在消防法规知识库中检索与用户问题相关的法规条文",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索问题或关键词"}
                },
                "required": ["query"],
            },
            handler=knowledge_search,
        ),
        AgentTool(
            name="statistics_summary",
            description="获取当前用户权限范围内的业务统计摘要（记录、任务、知识库计数）",
            parameters={"type": "object", "properties": {}},
            handler=statistics_summary,
        ),
    ]


def load_mcp_tools(settings: Settings | None = None) -> list[AgentTool]:
    """把 MCP_SERVERS 配置的服务器工具适配为 Agent 工具。

    单个服务器不可用（连接失败/响应非法）只记日志并跳过，不影响其余工具。
    """
    from app.mcp.client import MCPClient, load_mcp_servers

    s = settings or get_settings()
    try:
        servers = load_mcp_servers(s)
    except AppException as exc:
        logger.warning("MCP 配置不可用，跳过 MCP 工具加载: %s", exc.message)
        return []
    client = MCPClient(s)
    tools: list[AgentTool] = []
    for server in servers:
        try:
            remote_tools = client.list_tools(server)
        except AppException as exc:
            logger.warning("MCP 服务器 %s 工具列表获取失败，跳过: %s", server.name, exc.message)
            continue
        for remote in remote_tools:
            if not isinstance(remote, dict) or not remote.get("name"):
                continue

            def make_handler(srv=server, tool_name=str(remote["name"])):
                def handler(arguments: dict) -> str:
                    return client.call_tool(srv, tool_name, arguments)

                return handler

            parameters = remote.get("inputSchema")
            tools.append(
                AgentTool(
                    name=f"mcp__{server.name}__{remote['name']}",
                    description=str(remote.get("description") or f"MCP 工具 {remote['name']}"),
                    parameters=parameters
                    if isinstance(parameters, dict)
                    else {"type": "object", "properties": {}},
                    handler=make_handler(),
                )
            )
    return tools


# ---------- 多智能体编排 ----------


class AgentOrchestrator:
    """规划器 → 逐个执行（Agent + 工具子集）→ 汇总。"""

    def __init__(
        self,
        llm: LLMService,
        tools: list[AgentTool],
        *,
        max_steps: int,
        max_subtasks: int,
        timeout_seconds: float,
    ) -> None:
        self._llm = llm
        self._tools = {t.name: t for t in tools}
        self._max_steps = max_steps
        self._max_subtasks = max_subtasks
        self._timeout = timeout_seconds

    def run(self, goal: str) -> AgentResult:
        started = time.monotonic()
        subtasks = self._plan(goal)
        results: list[dict] = []
        steps: list[dict] = []
        tools_used: set[str] = set()
        for subtask in subtasks:
            remaining = self._timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise AppException(
                    "AGENT_TIMEOUT", "Agent 执行超时，请缩小目标范围后重试", 504
                )
            allowed = [
                self._tools[name]
                for name in subtask.get("tools") or []
                if name in self._tools
            ]
            agent = Agent(
                self._llm,
                allowed,
                max_steps=self._max_steps,
                timeout_seconds=remaining,
            )
            result = agent.run(str(subtask.get("task") or goal))
            results.append(
                {
                    "role": subtask.get("role") or "执行者",
                    "task": subtask.get("task"),
                    "answer": result.answer,
                }
            )
            steps.extend(result.steps)
            tools_used.update(result.tools_used)
        answer = self._summarize(goal, results)
        return AgentResult(answer=answer, steps=steps, tools_used=sorted(tools_used))

    def _plan(self, goal: str) -> list[dict]:
        """LLM 拆解目标；输出非法时回退为单个子任务（全工具集）。"""
        content = self._llm.chat(
            [
                {"role": "system", "content": get_prompt("agent.PLANNER")},
                {
                    "role": "user",
                    "content": build_planner_user_prompt(
                        goal, sorted(self._tools), self._max_subtasks
                    ),
                },
            ]
        )
        try:
            plan = json.loads(_strip_code_fence(content))
        except json.JSONDecodeError:
            logger.info("规划器输出非 JSON，回退为单个子任务")
            return [{"role": "执行者", "task": goal, "tools": sorted(self._tools)}]
        if not isinstance(plan, list) or not plan:
            return [{"role": "执行者", "task": goal, "tools": sorted(self._tools)}]
        subtasks = [s for s in plan if isinstance(s, dict)][: self._max_subtasks]
        return subtasks or [{"role": "执行者", "task": goal, "tools": sorted(self._tools)}]

    def _summarize(self, goal: str, results: list[dict]) -> str:
        if len(results) == 1:
            # 单子任务无需二次汇总，直接采用子任务回答
            return str(results[0]["answer"])
        return self._llm.chat(
            [
                {"role": "system", "content": get_prompt("agent.SUMMARIZER")},
                {"role": "user", "content": build_summarizer_user_prompt(goal, results)},
            ]
        )


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if len(lines) > 1 else []
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
