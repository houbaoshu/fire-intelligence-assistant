"""Minimal MCP client for HTTP-hosted MCP servers.

Implements the tool-list / tool-call surface of the Model Context Protocol
over HTTP. Servers configured via MCP_SERVERS env (JSON list):
    [{"name": "ref", "url": "https://mcp.example.com/mcp"}]

The client talks to a conforming MCP HTTP endpoint (JSON-RPC 2.0 over POST)
and exposes tools as callables for agents. Full spec conformance (SSE,
streamable HTTP upgrade, auth) is out of scope here but the interface is
stable so a richer transport can replace it without touching agents.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("mcp")


@dataclass
class MCPTool:
    name: str
    description: str
    server: str
    input_schema: dict = field(default_factory=dict)


class MCPClient:
    """Client for one MCP HTTP server."""

    def __init__(self, name: str, url: str, api_key: str | None = None):
        self.name = name
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._tools: list[MCPTool] | None = None

    def _rpc(self, method: str, params: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        with httpx.Client(timeout=60) as client:
            resp = client.post(self.url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"MCP {self.name} 调用失败:{resp.status_code}")
        data = resp.json()
        if "error" in data and data["error"]:
            raise RuntimeError(f"MCP {self.name} 错误:{data['error']}")
        return data.get("result", {})

    def list_tools(self) -> list[MCPTool]:
        if self._tools is None:
            result = self._rpc("tools/list", {})
            tools = result.get("tools", [])
            self._tools = [
                MCPTool(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    server=self.name,
                    input_schema=t.get("inputSchema", {}),
                )
                for t in tools
            ]
        return self._tools

    def call_tool(self, name: str, arguments: dict) -> str:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        content = result.get("content", [])
        return "\n".join(
            str(c.get("text", "")) for c in content if isinstance(c, dict)
        ) or json.dumps(result, ensure_ascii=False)[:500]


def configured_servers() -> list[MCPClient]:
    """Build clients from MCP_SERVERS env (JSON list of {name,url,api_key})."""
    raw = os.environ.get("MCP_SERVERS", "") or get_settings().MCP_SERVERS or ""
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("MCP_SERVERS 不是合法 JSON,已忽略")
        return []
    return [
        MCPClient(item.get("name", f"mcp-{i}"), item["url"], item.get("api_key"))
        for i, item in enumerate(items)
        if item.get("url")
    ]
