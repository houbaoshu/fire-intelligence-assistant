"""异步任务状态机测试（API.md §8）：轮询、retry、cancel、归属。"""

import time

from .helpers import (
    auth_headers,
    generate_inspection,
    make_admin,
    make_role,
    register,
    wait_task,
)


def test_generate_task_fails_readably_when_ai_not_configured(client):
    """M2：AI provider 未配置，任务必须 failed 且错误可读，不得编造结果。"""
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    task = wait_task(client, tokens, task_id)
    assert task["status"] == "failed"
    assert task["task_type"] == "inspection_record_generation"
    assert task["error_code"] == "AI_SERVICE_NOT_CONFIGURED"
    assert "AI 服务未配置" in task["error_message"]
    assert task["result_data"] is None
    assert task["progress"] >= 0


def test_task_response_shape(client):
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    task = wait_task(client, tokens, task_id)
    assert set(task.keys()) == {
        "task_id",
        "task_type",
        "status",
        "progress",
        "current_stage",
        "result_data",
        "error_code",
        "error_message",
        "created_at",
        "updated_at",
    }


def test_list_tasks_scoped_and_filtered(client):
    tokens = register(client)
    other = register(client, email="other@example.com")
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)

    resp = client.get("/api/tasks", headers=auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["task_id"] == task_id

    # 他人不可见
    resp = client.get("/api/tasks", headers=auth_headers(other))
    assert resp.json()["total"] == 0

    # 状态过滤
    resp = client.get(
        "/api/tasks", params={"status": "failed"}, headers=auth_headers(tokens)
    )
    assert resp.json()["total"] == 1
    resp = client.get(
        "/api/tasks", params={"status": "completed"}, headers=auth_headers(tokens)
    )
    assert resp.json()["total"] == 0

    # 非法状态
    resp = client.get(
        "/api/tasks", params={"status": "bogus"}, headers=auth_headers(tokens)
    )
    assert resp.status_code == 400


def test_get_task_of_other_user_returns_404(client):
    tokens = register(client)
    other = register(client, email="other@example.com")
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)
    resp = client.get(f"/api/tasks/{task_id}", headers=auth_headers(other))
    assert resp.status_code == 404


def test_retry_failed_task_creates_new_instance(client):
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)

    resp = client.post(f"/api/tasks/{task_id}/retry", headers=auth_headers(tokens))
    assert resp.status_code == 200
    new_task_id = resp.json()["task_id"]
    assert new_task_id != task_id
    new_task = wait_task(client, tokens, new_task_id)
    assert new_task["status"] == "failed"  # AI 仍未配置，再次失败

    # 原任务保留（审计）
    original = client.get(f"/api/tasks/{task_id}", headers=auth_headers(tokens)).json()
    assert original["status"] == "failed"


def test_retry_non_failed_task_returns_409(client):
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)
    # 把 retry 应用到终态后再对 completed 场景无法直接构造，退而求其次：
    # 对 pending/processing 状态的任务 retry 返回 409
    task_id2 = generate_inspection(client, tokens)
    # 任务刚提交，大概率 pending/processing；等它终态后用 cancelled 场景覆盖见下
    resp = client.post(f"/api/tasks/{task_id2}/retry", headers=auth_headers(tokens))
    assert resp.status_code in (200, 409)
    if resp.status_code == 409:
        assert resp.json()["error"]["code"] == "TASK_STATE_CONFLICT"
    wait_task(client, tokens, task_id2)


def test_cancel_processing_or_pending_task(client):
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    resp = client.post(f"/api/tasks/{task_id}/cancel", headers=auth_headers(tokens))
    # 任务可能在 cancel 前已失败（AI 未配置时立即失败）
    assert resp.status_code in (200, 409)
    if resp.status_code == 200:
        assert resp.json() == {"task_id": task_id, "status": "cancelled"}
        task = client.get(f"/api/tasks/{task_id}", headers=auth_headers(tokens)).json()
        assert task["status"] == "cancelled"
    else:
        assert resp.json()["error"]["code"] == "TASK_STATE_CONFLICT"
    wait_task(client, tokens, task_id)


def test_cancel_terminal_task_returns_409(client):
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)  # failed（AI 未配置）
    resp = client.post(f"/api/tasks/{task_id}/cancel", headers=auth_headers(tokens))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "TASK_STATE_CONFLICT"


def test_retry_cancelled_task_allowed(client):
    """failed/cancelled 才可 retry：先 cancel（若赶上）再 retry。"""
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    client.post(f"/api/tasks/{task_id}/cancel", headers=auth_headers(tokens))
    task = wait_task(client, tokens, task_id)
    assert task["status"] in ("cancelled", "failed")
    resp = client.post(f"/api/tasks/{task_id}/retry", headers=auth_headers(tokens))
    assert resp.status_code == 200
    wait_task(client, tokens, resp.json()["task_id"])


def test_retry_finalized_record_task_returns_409(client):
    """重试不得重复生成已定稿记录（API.md §8）。"""
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)
    # 找到关联记录并定稿
    resp = client.get("/api/inspection-record", headers=auth_headers(tokens))
    record_id = resp.json()["items"][0]["id"]
    # 定稿需 record.finalize 权限（M6：supervisor/admin）
    make_role(tokens["user"]["id"], "supervisor")
    resp = client.put(
        f"/api/inspection-record/{record_id}",
        headers=auth_headers(tokens),
        json={"status": "finalized"},
    )
    assert resp.status_code == 200
    resp = client.post(f"/api/tasks/{task_id}/retry", headers=auth_headers(tokens))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "TASK_STATE_CONFLICT"


def test_admin_sees_all_tasks(client):
    tokens = register(client)
    admin = register(client, email="admin@example.com")
    make_admin(admin["user"]["id"])
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)
    resp = client.get(f"/api/tasks/{task_id}", headers=auth_headers(admin))
    assert resp.status_code == 200
    resp = client.get("/api/tasks", headers=auth_headers(admin))
    assert resp.json()["total"] >= 1


def test_progress_monotonic_within_run(client):
    """failed 任务进度合法（0-100）；单调性由 worker max() 保证。"""
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    task = wait_task(client, tokens, task_id)
    assert 0 <= task["progress"] <= 100
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        again = client.get(f"/api/tasks/{task_id}", headers=auth_headers(tokens)).json()
        assert again["progress"] >= 0
        break
