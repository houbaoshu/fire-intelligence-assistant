"""MCP HTTP JSON-RPC 客户端（M8）。

- 服务器经环境变量 ``MCP_SERVERS`` 配置（JSON 数组：
  ``[{"name": "...", "url": "...", "token_ref": "密钥环境变量名"}]``）；
  token_ref 只存环境变量名，密钥从该变量解析，不落库不落日志。
- 实现 ``tools/list`` 与 ``tools/call`` 两个方法；超时与错误一律可读
  （AppException MCP_*），绝不吞错。
- MCP 工具经 ``load_mcp_tools`` 适配为 Agent 工具（app/services/ai/agent.py）。
"""

import itertools
import json
import os
from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger("mcp.client")

_request_ids = itertools.count(1)


def mcp_error(message: str) -> AppException:
    return AppException("MCP_SERVER_ERROR", message, 502)


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    url: str
    token: str  # 已从 token_ref 环境变量解析；为空表示无需鉴权


def load_mcp_servers(settings: Settings | None = None) -> list[MCPServerConfig]:
    """解析 MCP_SERVERS 环境变量；格式非法抛可读错误。"""
    s = settings or get_settings()
    raw = s.MCP_SERVERS.strip()
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        raise AppException(
            "MCP_CONFIG_ERROR", "MCP_SERVERS 配置不是合法 JSON 数组，请检查环境变量", 500
        )
    if not isinstance(items, list):
        raise AppException("MCP_CONFIG_ERROR", "MCP_SERVERS 必须是 JSON 数组", 500)
    servers = []
    for item in items:
        if not isinstance(item, dict) or not item.get("name") or not item.get("url"):
            raise AppException(
                "MCP_CONFIG_ERROR", "MCP_SERVERS 数组元素必须包含 name 与 url", 500
            )
        token_ref = item.get("token_ref")
        # token_ref 只存环境变量名；密钥从此处唯一入口解析
        token = os.environ.get(token_ref, "") if token_ref else ""
        servers.append(MCPServerConfig(name=item["name"], url=item["url"], token=token))
    return servers


class MCPClient:
    """MCP 服务器的最小 JSON-RPC over HTTP 客户端（同步 httpx + 超时）。"""

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._transport = transport

    def list_tools(self, server: MCPServerConfig) -> list[dict]:
        result = self._rpc(server, "tools/list", {})
        tools = result.get("tools") if isinstance(result, dict) else None
        if not isinstance(tools, list):
            raise mcp_error(f"MCP 服务器 {server.name} 的 tools/list 响应无法解析")
        return tools

    def call_tool(self, server: MCPServerConfig, name: str, arguments: dict) -> str:
        """调用工具，返回文本结果（多个 content 片段拼接）。"""
        result = self._rpc(server, "tools/call", {"name": name, "arguments": arguments})
        if isinstance(result, dict) and result.get("isError"):
            raise mcp_error(f"MCP 工具 {name} 执行失败（服务器 {server.name} 返回错误）")
        contents = result.get("content") if isinstance(result, dict) else None
        if isinstance(contents, list):
            texts = [
                str(c.get("text", "")) for c in contents if isinstance(c, dict)
            ]
            text = "\n".join(t for t in texts if t)
            if text:
                return text
        # 兼容非标准但常见的直接文本/结构化结果
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, default=str)

    def _rpc(self, server: MCPServerConfig, method: str, params: dict) -> object:
        payload = {
            "jsonrpc": "2.0",
            "id": next(_request_ids),
            "method": method,
            "params": params,
        }
        headers = {"Content-Type": "application/json"}
        if server.token:
            headers["Authorization"] = f"Bearer {server.token}"
        try:
            with httpx.Client(
                timeout=self._settings.MCP_TIMEOUT_SECONDS, transport=self._transport
            ) as client:
                resp = client.post(server.url, json=payload, headers=headers)
        except httpx.TimeoutException:
            raise mcp_error(
                f"MCP 服务器 {server.name} 请求超时（>{self._settings.MCP_TIMEOUT_SECONDS:.0f}s）"
            )
        except httpx.TransportError:
            raise mcp_error(f"MCP 服务器 {server.name} 无法连接，请检查配置与网络")
        if resp.status_code >= 400:
            raise mcp_error(
                f"MCP 服务器 {server.name} 拒绝请求（HTTP {resp.status_code}）"
            )
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            raise mcp_error(f"MCP 服务器 {server.name} 返回了非 JSON 响应")
        if not isinstance(data, dict):
            raise mcp_error(f"MCP 服务器 {server.name} 返回了无法解析的响应")
        if data.get("error"):
            error = data["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise mcp_error(f"MCP 服务器 {server.name} 返回错误：{message}")
        return data.get("result")
