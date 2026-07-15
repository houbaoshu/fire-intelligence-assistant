from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    correlation_id: str


@dataclass(frozen=True)
class ToolResult:
    content: dict[str, Any]
    is_error: bool = False


class Agent(Protocol):
    def run(self, objective: str, context: dict[str, Any]) -> dict[str, Any]: ...


class ToolProvider(Protocol):
    """Provider-neutral contract for local tools, MCP servers, and plugins."""

    def list_tools(self) -> list[dict[str, Any]]: ...

    def call(self, request: ToolCall) -> ToolResult: ...


class ModelRouter(Protocol):
    def select(self, capability: str, constraints: dict[str, Any]) -> str: ...


class WorkflowExecutor(Protocol):
    def execute(self, definition: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]: ...
