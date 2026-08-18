"""Milestone 8 AI 平台测试：Prompt 管理、模型路由、评估、插件、MCP、Agent。

全部外部 HTTP 调用经 httpx.MockTransport 或注入替身 mock，不触网。
"""

import json
import os

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import AppException
from app.rag.query import QAResult
from tests.helpers import auth_headers, make_admin, make_role, register


# ---------- 通用辅助 ----------


def _admin_client(client):
    tokens = register(client, email="admin-m8@example.com")
    make_admin(tokens["user"]["id"])
    return tokens


@pytest.fixture
def db_session():
    from app.db import SessionLocal

    with SessionLocal() as session:
        yield session


# ---------- Prompt 管理 ----------


def test_prompt_seeds_visible(client):
    tokens = _admin_client(client)
    resp = client.get("/api/admin/prompts", headers=auth_headers(tokens))
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    by_key = {}
    for item in items:
        by_key.setdefault(item["key"], []).append(item)
    assert "qa.QA_SYSTEM" in by_key
    seed = by_key["qa.QA_SYSTEM"][0]
    assert seed["version"] == 1 and seed["is_active"] is True
    assert seed["content"]  # 种子内容非空


def test_prompts_require_admin(client):
    tokens = register(client, email="viewer-m8@example.com")
    make_role(tokens["user"]["id"], "viewer")
    resp = client.get("/api/admin/prompts", headers=auth_headers(tokens))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_prompt_version_and_activate_flow(client):
    tokens = _admin_client(client)
    headers = auth_headers(tokens)
    create = client.post(
        "/api/admin/prompts/qa.QA_SYSTEM/versions",
        headers=headers,
        json={"content": "新的问答系统 Prompt", "name": "v2 草稿"},
    )
    assert create.status_code == 200, create.text
    draft = create.json()
    assert draft["version"] == 2 and draft["is_active"] is False

    activate = client.post(f"/api/admin/prompts/{draft['id']}/activate", headers=headers)
    assert activate.status_code == 200, activate.text
    assert activate.json() == {"id": draft["id"], "is_active": True}

    items = client.get("/api/admin/prompts", headers=headers).json()["items"]
    qa_versions = [i for i in items if i["key"] == "qa.QA_SYSTEM"]
    actives = [i for i in qa_versions if i["is_active"]]
    assert len(actives) == 1 and actives[0]["id"] == draft["id"]


def test_prompt_create_unknown_key_404(client):
    tokens = _admin_client(client)
    resp = client.post(
        "/api/admin/prompts/unknown.KEY/versions",
        headers=auth_headers(tokens),
        json={"content": "x"},
    )
    assert resp.status_code == 404


def test_get_prompt_db_priority_and_fallback(db_session):
    from app.models.ai_platform import PromptVersion
    from app.prompts.qa import QA_SYSTEM_PROMPT
    from app.services.prompt_service import PromptService, get_prompt

    PromptService(db_session).seed()
    db_session.commit()
    # DB 生效版本优先
    assert get_prompt("qa.QA_SYSTEM", db_session) == QA_SYSTEM_PROMPT
    row = PromptVersion(
        key="qa.QA_SYSTEM", content="DB 定制版本", version=99, is_active=True
    )
    db_session.add(row)
    # 关闭原种子生效版本
    for old in PromptService(db_session).list_versions():
        if old.key == "qa.QA_SYSTEM" and old.id != row.id:
            old.is_active = False
    db_session.commit()
    assert get_prompt("qa.QA_SYSTEM", db_session) == "DB 定制版本"
    # 无生效版本回退代码常量
    row.is_active = False
    db_session.commit()
    assert get_prompt("qa.QA_SYSTEM", db_session) == QA_SYSTEM_PROMPT
    with pytest.raises(KeyError):
        get_prompt("no.such.key", db_session)


# ---------- 模型管理与路由 ----------


def _llm_settings(**overrides) -> Settings:
    base = {
        "AI_LLM_API_KEY": "env-key",
        "AI_LLM_MODEL": "env-model",
        "AI_LLM_BASE_URL": "https://llm.example.com/v1",
    }
    base.update(overrides)
    return Settings(**base)


def test_model_crud_endpoints(client):
    tokens = _admin_client(client)
    headers = auth_headers(tokens)
    create = client.post(
        "/api/admin/models",
        headers=headers,
        json={
            "name": "主用 LLM",
            "kind": "llm",
            "provider": "openai",
            "model_name": "gpt-x",
            "base_url": "https://api.example.com/v1",
            "api_key_ref": "MY_LLM_KEY",
            "priority": 10,
        },
    )
    assert create.status_code == 200, create.text
    item = create.json()
    assert item["kind"] == "llm" and item["is_active"] is True
    # 密钥不落库：响应中只有环境变量名
    assert item["api_key_ref"] == "MY_LLM_KEY"

    listing = client.get("/api/admin/models", headers=headers)
    assert any(i["id"] == item["id"] for i in listing.json()["items"])

    update = client.put(
        f"/api/admin/models/{item['id']}", headers=headers, json={"is_active": False}
    )
    assert update.json()["is_active"] is False

    delete = client.delete(f"/api/admin/models/{item['id']}", headers=headers)
    assert delete.json() == {"id": item["id"], "deleted": True}
    assert client.delete(f"/api/admin/models/{item['id']}", headers=headers).status_code == 404


def test_models_invalid_kind_400(client):
    tokens = _admin_client(client)
    resp = client.post(
        "/api/admin/models",
        headers=auth_headers(tokens),
        json={"name": "x", "kind": "bogus", "provider": "p", "model_name": "m"},
    )
    assert resp.status_code == 400


def test_models_require_admin(client):
    tokens = register(client, email="inspector-m8@example.com")
    resp = client.get("/api/admin/models", headers=auth_headers(tokens))
    assert resp.status_code == 403


def test_model_routing_priority_and_fallback(db_session, monkeypatch):
    from app.models.ai_platform import ModelConfiguration
    from app.services.ai.providers import resolve_capability_config

    settings = _llm_settings()
    # 无 DB 配置：回退环境变量
    config = resolve_capability_config("llm", settings=settings, session=db_session)
    assert config is not None
    assert config.source == "environment" and config.model == "env-model"

    # 插入两条生效配置：priority 小者优先；api_key 从 api_key_ref 环境变量解析
    monkeypatch.setenv("DB_LLM_KEY", "db-secret")
    low = ModelConfiguration(
        name="备用", kind="llm", provider="b", model_name="model-b",
        base_url="https://b.example.com/v1", api_key_ref="DB_LLM_KEY",
        is_active=True, priority=50,
    )
    high = ModelConfiguration(
        name="主用", kind="llm", provider="a", model_name="model-a",
        base_url="https://a.example.com/v1", api_key_ref="DB_LLM_KEY",
        is_active=True, priority=10,
    )
    db_session.add_all([low, high])
    db_session.commit()
    config = resolve_capability_config("llm", settings=settings, session=db_session)
    assert config.source == "database"
    assert config.model == "model-a" and config.api_key == "db-secret"

    # 主用失效后按优先级落到备用
    high.is_active = False
    db_session.commit()
    config = resolve_capability_config("llm", settings=settings, session=db_session)
    assert config.model == "model-b"

    # api_key_ref 指向的环境变量缺失 → 该配置不完整被跳过，回退环境变量
    low.api_key_ref = "MISSING_KEY_ENV"
    db_session.commit()
    config = resolve_capability_config("llm", settings=settings, session=db_session)
    assert config.source == "environment"


def test_providers_is_configured_via_db(db_session):
    from app.models.ai_platform import ModelConfiguration
    from app.services.ai.providers import AIProviders

    # 环境变量未配置 llm，但 DB 有完整生效配置 → 视为已配置
    settings = _llm_settings(AI_LLM_API_KEY="", AI_LLM_MODEL="", AI_LLM_BASE_URL="")
    assert not AIProviders(settings).is_configured("llm", session=db_session)
    db_session.add(
        ModelConfiguration(
            name="主用", kind="llm", provider="a", model_name="model-a",
            base_url="https://a.example.com/v1", api_key_ref=None,
            is_active=True, priority=10,
        )
    )
    db_session.commit()
    # api_key_ref 为空时回退该 kind 的环境变量密钥；此处也为空 → 不完整
    assert not AIProviders(settings).is_configured("llm", session=db_session)
    monkey = os.environ
    monkey["LLM_KEY_FROM_REF"] = "ref-secret"
    try:
        row = db_session.query(ModelConfiguration).one()
        row.api_key_ref = "LLM_KEY_FROM_REF"
        db_session.commit()
        assert AIProviders(settings).is_configured("llm", session=db_session)
    finally:
        del monkey["LLM_KEY_FROM_REF"]


# ---------- 评估 ----------


def _fake_qa_result(answer: str, sources: list | None = None) -> QAResult:
    return QAResult(answer=answer, sources=sources or [])


def test_evaluation_scoring_rules(client, monkeypatch):
    from app.services import evaluation_service

    answers = {
        "q1": _fake_qa_result("根据《消防法》第十六条回答", sources=[{"title": "消防法"}]),
        "q2": _fake_qa_result("没有依据", sources=[]),
        "q3": _fake_qa_result("未检索到可靠依据", sources=[]),
    }
    monkeypatch.setattr(
        evaluation_service, "run_query", lambda session, q: answers[q]
    )
    tokens = _admin_client(client)
    resp = client.post(
        "/api/admin/evaluations",
        headers=auth_headers(tokens),
        json={
            "name": "回归评估",
            "questions": [
                {"question": "q1", "expected_keywords": ["消防法", "第十六条"], "require_source": True},
                {"question": "q2", "expected_keywords": ["消防法"]},
                {"question": "q3", "expect_refusal": True},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["total_questions"] == 3
    assert body["passed"] == 2  # q1 通过；q2 关键词未命中；q3 拒答得当
    details = {d["question"]: d for d in body["details"]}
    assert details["q1"]["passed"] is True
    kw_check = details["q2"]["checks"][0]
    assert kw_check["rule"] == "expected_keywords" and kw_check["hit_rate"] == 0.0
    assert details["q3"]["passed"] is True


def test_evaluation_pipeline_error_recorded(client, monkeypatch):
    from app.services import evaluation_service
    from app.services.ai.http_client import ai_not_configured

    def _raise(session, q):
        raise ai_not_configured("llm")

    monkeypatch.setattr(evaluation_service, "run_query", _raise)
    tokens = _admin_client(client)
    resp = client.post(
        "/api/admin/evaluations",
        headers=auth_headers(tokens),
        json={"name": "异常评估", "questions": [{"question": "任意"}]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["passed"] == 0
    assert "AI_SERVICE_NOT_CONFIGURED" in body["details"][0]["error"]


def test_evaluation_list_and_detail(client, monkeypatch):
    from app.services import evaluation_service

    monkeypatch.setattr(
        evaluation_service, "run_query",
        lambda session, q: _fake_qa_result("回答", sources=[{"title": "t"}]),
    )
    tokens = _admin_client(client)
    headers = auth_headers(tokens)
    created = client.post(
        "/api/admin/evaluations",
        headers=headers,
        json={"name": "列表评估", "questions": [{"question": "q"}]},
    ).json()

    listing = client.get("/api/admin/evaluations", headers=headers)
    assert listing.status_code == 200
    page = listing.json()
    assert page["total"] == 1
    assert "details" not in page["items"][0]  # 列表不含 details

    detail = client.get(f"/api/admin/evaluations/{created['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["details"]


def test_evaluations_require_admin(client):
    tokens = register(client, email="viewer-eval@example.com")
    make_role(tokens["user"]["id"], "viewer")
    resp = client.get("/api/admin/evaluations", headers=auth_headers(tokens))
    assert resp.status_code == 403


# ---------- 插件 ----------


def test_plugins_list_and_toggle(client):
    tokens = _admin_client(client)
    headers = auth_headers(tokens)
    resp = client.get("/api/admin/plugins", headers=headers)
    assert resp.status_code == 200, resp.text
    items = {i["name"]: i for i in resp.json()["items"]}
    assert {"task_terminal_logger", "qa_disclaimer"} <= set(items)
    plugin = items["qa_disclaimer"]
    assert plugin["enabled"] is True
    assert plugin["entry_point"] == "app.plugins.builtin.qa_disclaimer"

    off = client.put(f"/api/admin/plugins/{plugin['id']}", headers=headers, json={"enabled": False})
    assert off.status_code == 200 and off.json()["enabled"] is False
    on = client.put(f"/api/admin/plugins/{plugin['id']}", headers=headers, json={"enabled": True})
    assert on.json()["enabled"] is True


def test_qa_disclaimer_hook_enabled_disabled(client, db_session, monkeypatch):
    from app.services import qa_service
    from app.services.plugin_service import PluginService

    monkeypatch.setattr(
        qa_service, "run_query",
        lambda session, q: _fake_qa_result("根据 [1] 的回答", sources=[]),
    )
    PluginService(db_session).register_builtin()
    db_session.commit()
    tokens = register(client, email="qa-plugin@example.com")

    enabled = client.post(
        "/api/qa/query", headers=auth_headers(tokens), json={"question": "问题"}
    )
    assert enabled.status_code == 200, enabled.text
    assert "免责声明" in enabled.json()["answer"]

    # 禁用后不再追加
    from app.models.ai_platform import Plugin

    row = db_session.query(Plugin).filter_by(name="qa_disclaimer").one()
    row.enabled = False
    db_session.commit()
    disabled = client.post(
        "/api/qa/query", headers=auth_headers(tokens), json={"question": "问题"}
    )
    assert "免责声明" not in disabled.json()["answer"]


def test_task_terminal_hook_runs(db_session):
    from app.plugins import run_hook
    from app.services.plugin_service import PluginService

    PluginService(db_session).register_builtin()
    db_session.commit()
    context = run_hook(
        db_session,
        "on_task_terminal",
        {"task_id": "t-1", "task_type": "video_analysis", "status": "completed",
         "error_message": None},
    )
    assert context["status"] == "completed"


# ---------- MCP ----------


def _mcp_settings() -> Settings:
    return Settings(MCP_SERVERS=json.dumps([
        {"name": "fs", "url": "https://mcp.example.com/rpc", "token_ref": "MCP_FS_TOKEN"}
    ]))


def test_mcp_list_and_call_tools(monkeypatch):
    from app.mcp.client import MCPClient, load_mcp_servers

    monkeypatch.setenv("MCP_FS_TOKEN", "mcp-secret")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        if payload["method"] == "tools/list":
            return httpx.Response(200, json={
                "jsonrpc": "2.0", "id": payload["id"],
                "result": {"tools": [{"name": "read_file", "description": "读文件"}]},
            })
        if payload["method"] == "tools/call":
            assert payload["params"] == {"name": "read_file", "arguments": {"path": "/a"}}
            return httpx.Response(200, json={
                "jsonrpc": "2.0", "id": payload["id"],
                "result": {"content": [{"type": "text", "text": "文件内容"}]},
            })
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": {}})

    servers = load_mcp_servers(_mcp_settings())
    assert len(servers) == 1 and servers[0].token == "mcp-secret"
    client = MCPClient(_mcp_settings(), transport=httpx.MockTransport(handler))
    tools = client.list_tools(servers[0])
    assert tools[0]["name"] == "read_file"
    assert client.call_tool(servers[0], "read_file", {"path": "/a"}) == "文件内容"
    assert requests[0].headers["Authorization"] == "Bearer mcp-secret"


def test_mcp_error_handling():
    from app.mcp.client import MCPClient, MCPServerConfig

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        return httpx.Response(200, json={
            "jsonrpc": "2.0", "id": payload["id"],
            "error": {"code": -32601, "message": "method not found"},
        })

    server = MCPServerConfig(name="bad", url="https://mcp.example.com/rpc", token="")
    client = MCPClient(Settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(AppException) as exc_info:
        client.list_tools(server)
    assert exc_info.value.code == "MCP_SERVER_ERROR"
    assert "method not found" in exc_info.value.message


def test_mcp_invalid_config():
    from app.mcp.client import load_mcp_servers

    with pytest.raises(AppException) as exc_info:
        load_mcp_servers(Settings(MCP_SERVERS="{not-json"))
    assert exc_info.value.code == "MCP_CONFIG_ERROR"
    assert load_mcp_servers(Settings(MCP_SERVERS="")) == []


# ---------- Agent 与多智能体 ----------


class _FakeLLM:
    """按脚本返回 function-calling 响应的假 LLM（测试专用）。"""

    def __init__(self, raw_script: list[dict], chat_script: list[str] | None = None):
        self._raw = list(raw_script)
        self._chat = list(chat_script or [])

    def chat_raw(self, messages, *, temperature=0.2, tools=None):
        assert self._raw, "脚本耗尽"
        return self._raw.pop(0)

    def chat(self, messages, *, temperature=0.2):
        assert self._chat, "chat 脚本耗尽"
        return self._chat.pop(0)


def _tool_call_message(name: str, arguments: dict, call_id: str = "c1") -> dict:
    return {
        "content": None,
        "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)},
        }],
    }


def test_agent_function_calling_loop():
    from app.services.ai.agent import Agent, AgentTool

    tool = AgentTool(
        name="echo",
        description="回声",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        handler=lambda args: f"echo:{args['text']}",
    )
    llm = _FakeLLM([
        _tool_call_message("echo", {"text": "hi"}),
        {"content": "最终回答"},
    ])
    agent = Agent(llm, [tool], max_steps=4, timeout_seconds=30)
    result = agent.run("任务")
    assert result.answer == "最终回答"
    assert result.tools_used == ["echo"]
    assert result.steps[0]["summary"] == "echo:hi"


def test_agent_step_limit():
    from app.services.ai.agent import Agent, AgentTool

    tool = AgentTool(
        name="noop", description="无操作",
        parameters={"type": "object", "properties": {}}, handler=lambda args: "ok",
    )
    llm = _FakeLLM([_tool_call_message("noop", {})] * 5)
    agent = Agent(llm, [tool], max_steps=2, timeout_seconds=30)
    with pytest.raises(AppException) as exc_info:
        agent.run("任务")
    assert exc_info.value.code == "AGENT_STEP_LIMIT"


def test_agent_tool_error_fed_back():
    from app.services.ai.agent import Agent, AgentTool
    from app.services.ai.http_client import ai_not_configured

    def _fail(_):
        raise ai_not_configured("embedding")

    tool = AgentTool(
        name="knowledge_search", description="检索",
        parameters={"type": "object", "properties": {}}, handler=_fail,
    )
    llm = _FakeLLM([
        _tool_call_message("knowledge_search", {}),
        {"content": "无法检索，如实说明"},
    ])
    agent = Agent(llm, [tool], max_steps=4, timeout_seconds=30)
    result = agent.run("任务")
    assert result.answer == "无法检索，如实说明"
    assert "未配置" in result.steps[0]["summary"]


def test_orchestrator_plan_execute_summarize():
    from app.services.ai.agent import AgentOrchestrator, AgentTool

    tool = AgentTool(
        name="statistics_summary", description="统计",
        parameters={"type": "object", "properties": {}},
        handler=lambda args: "记录总数 3",
    )
    plan = json.dumps([
        {"role": "检索员", "task": "子任务1", "tools": ["statistics_summary"]},
        {"role": "分析员", "task": "子任务2", "tools": []},
    ])
    llm = _FakeLLM(
        raw_script=[
            _tool_call_message("statistics_summary", {}),
            {"content": "子任务1回答"},
            {"content": "子任务2回答"},
        ],
        chat_script=[plan, "汇总后的最终回答"],
    )
    orchestrator = AgentOrchestrator(
        llm, [tool], max_steps=4, max_subtasks=4, timeout_seconds=30
    )
    result = orchestrator.run("总体目标")
    assert result.answer == "汇总后的最终回答"
    assert result.tools_used == ["statistics_summary"]
    assert len(result.steps) == 1


def test_orchestrator_invalid_plan_fallback():
    from app.services.ai.agent import AgentOrchestrator

    llm = _FakeLLM(raw_script=[{"content": "直接回答"}], chat_script=["非 JSON 规划"])
    orchestrator = AgentOrchestrator(llm, [], max_steps=4, max_subtasks=4, timeout_seconds=30)
    result = orchestrator.run("目标")
    assert result.answer == "直接回答"  # 单子任务跳过二次汇总


def test_agent_run_endpoint_llm_not_configured(client):
    tokens = register(client, email="agent-user@example.com")
    resp = client.post(
        "/api/agent/run", headers=auth_headers(tokens), json={"goal": "统计一下"}
    )
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "AI_SERVICE_NOT_CONFIGURED"


def test_agent_run_permission(client):
    tokens = register(client, email="agent-viewer@example.com")
    make_role(tokens["user"]["id"], "viewer")
    resp = client.post(
        "/api/agent/run", headers=auth_headers(tokens), json={"goal": "x"}
    )
    assert resp.status_code == 403
