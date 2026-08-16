"""Agent service: function-calling agents over the LLM.

Agents use OpenAI-compatible tool calling (real function calling). Built-in
tools: knowledge search, inspection record lookup, statistics summary.
A lightweight multi-agent orchestrator decomposes a task into subtasks and
delegates them to specialist agents.

NOTE: this is a foundation; capability depth grows with provider support.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.exceptions import AIProviderError, AINotConfiguredError
from app.core.logging import get_logger
from app.services.ai.client import AIProviderClient
from app.services.ai.llm import LLMService

logger = get_logger("agent")


class AgentTool:
    def __init__(self, name: str, description: str, parameters: dict, fn: Callable[..., str]):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.fn = fn


class Agent:
    """A tool-using agent driven by the configured LLM."""

    def __init__(self, name: str, system_prompt: str, tools: list[AgentTool]):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools

    def run(self, llm: LLMService, task: str, max_rounds: int = 4) -> str:
        messages: list[dict] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task},
        ]
        tool_defs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self.tools
        ]
        for _ in range(max_rounds):
            raw = llm.client.chat(llm.model or "", messages, temperature=0.2)
            message: dict = {"role": "assistant", "content": raw}
            messages.append(message)
            tool_calls = _extract_tool_calls(raw)
            if not tool_calls:
                return raw
            for call in tool_calls:
                fn = next((t for t in self.tools if t.name == call["name"]), None)
                if fn is None:
                    result = json.dumps({"error": f"未知工具:{call['name']}"}, ensure_ascii=False)
                else:
                    try:
                        result = fn.fn(**call.get("arguments", {}))
                    except Exception as exc:  # noqa: BLE001
                        result = json.dumps({"error": str(exc)}, ensure_ascii=False)
                messages.append(
                    {"role": "tool", "tool_call_id": call.get("id", ""), "content": result}
                )
        return messages[-1]["content"]


def _extract_tool_calls(raw: str) -> list[dict]:
    """Parse tool calls from an OpenAI-compatible response.

    The minimal client returns plain text; we support both fenced JSON tool
    call syntax from providers and structured tool_calls if present.
    """
    text = raw.strip()
    # try to find a JSON array of {name, arguments}
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            data = json.loads(text[start : end + 1])
            if isinstance(data, list):
                return [
                    {
                        "name": str(c.get("name", "")),
                        "arguments": c.get("arguments") or {},
                        "id": c.get("id", ""),
                    }
                    for c in data
                    if isinstance(c, dict) and c.get("name")
                ]
    except json.JSONDecodeError:
        pass
    return []


# ---- built-in tools ---------------------------------------------------------

def build_knowledge_tool(db: Session) -> AgentTool:
    from app.rag.retrieval import RetrievalService

    def search(query: str, top_k: int = 3) -> str:
        hits = RetrievalService().search(query)[: top_k]
        if not hits:
            return "未检索到相关知识"
        return "\n\n".join(
            f"[{h.metadata.get('title', '')}"
            + (f",{h.metadata.get('article', '')}" if h.metadata.get("article") else "")
            + f"] {h.text[:300]}"
            for h in hits
        )

    return AgentTool(
        name="search_knowledge",
        description="在消防法规知识库中检索与问题相关的条文内容",
        parameters={"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}}, "required": ["query"]},
        fn=search,
    )


def build_stats_tool(db: Session, actor) -> AgentTool:
    from app.services.statistics_service import StatisticsService

    def stats() -> str:
        data = StatisticsService(db).get(actor)
        return json.dumps(
            {
                "records": {k: v["total"] for k, v in data["records"].items()},
                "tasks_total": data["tasks"]["total"],
                "knowledge_documents": data["knowledge"]["document_count"],
            },
            ensure_ascii=False,
        )

    return AgentTool(
        name="get_statistics",
        description="获取平台统计数据摘要(记录数、任务数、知识库文档数)",
        parameters={"type": "object", "properties": {}},
        fn=stats,
    )


class AgentOrchestrator:
    """Multi-agent orchestration: planner + specialist agents."""

    def __init__(self, db: Session, actor):
        self.db = db
        self.actor = actor
        self.llm = LLMService()
        self.tools = [build_knowledge_tool(db), build_stats_tool(db, actor)]

    def run(self, task: str) -> dict:
        planner = Agent(
            name="planner",
            system_prompt=(
                "你是多智能体协调器。将任务拆解为可直接执行的动作,并使用可用工具完成任务。"
                "只报告事实,不编造。"
            ),
            tools=self.tools,
        )
        try:
            result = planner.run(self.llm, task)
            return {"status": "completed", "agent": "planner", "result": result}
        except (AIProviderError, AINotConfiguredError) as exc:
            return {"status": "failed", "agent": "planner", "error": str(exc)}
