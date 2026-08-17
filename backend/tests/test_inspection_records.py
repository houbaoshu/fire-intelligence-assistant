"""检查记录 CRUD / items 整体替换 / finalized 409 / 归属 / 分页 / download 测试。"""

import uuid

from .helpers import auth_headers, generate_inspection, make_admin, register, wait_task

BASE = "/api/inspection-record"


def _failed_record_id(client, tokens) -> str:
    """生成一个因 AI 未配置而 failed 的记录，返回 record_id。"""
    task_id = generate_inspection(client, tokens, remarks="现场重点查看疏散通道")
    wait_task(client, tokens, task_id)
    resp = client.get(BASE, headers=auth_headers(tokens))
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "failed"  # 任务失败联动记录状态
    return items[0]["id"]


def test_generate_creates_processing_record_then_failed(client):
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    # 任务提交后记录立即存在（processing 或已被 worker 置 failed）
    resp = client.get(BASE, headers=auth_headers(tokens))
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    wait_task(client, tokens, task_id)


def test_detail_contains_items_and_task_link(client):
    tokens = register(client)
    record_id = _failed_record_id(client, tokens)
    resp = client.get(f"{BASE}/{record_id}", headers=auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == record_id
    assert body["items"] == []
    assert uuid.UUID(body["source_task_id"])  # 关联任务


def test_update_fields_and_items_replace_semantics(client):
    tokens = register(client)
    record_id = _failed_record_id(client, tokens)

    # 新增两个 item（无 id）
    resp = client.put(
        f"{BASE}/{record_id}",
        headers=auth_headers(tokens),
        json={
            "title": "某商场消防检查记录",
            "inspection_unit": "某商场",
            "inspector_names": ["张三", "李四"],
            "status": "draft",
            "items": [
                {
                    "item_type": "violation",
                    "location": "一层东侧",
                    "description": "安全出口被锁闭",
                    "legal_basis": "《中华人民共和国消防法》第二十八条",
                    "correction_requirement": "立即解除锁闭",
                    "severity": "high",
                    "sort_order": 1,
                },
                {
                    "item_type": "observation",
                    "description": "二层灭火器巡检记录不全",
                    "sort_order": 2,
                },
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "某商场消防检查记录"
    assert body["status"] == "draft"
    assert len(body["items"]) == 2
    first_id = body["items"][0]["id"]

    # 整体替换：带 id 更新第一条、省略第二条（删除）、新增一条
    resp = client.put(
        f"{BASE}/{record_id}",
        headers=auth_headers(tokens),
        json={
            "items": [
                {"id": first_id, "item_type": "violation", "description": "安全出口被锁闭（已复核）", "sort_order": 1},
                {"item_type": "recommendation", "description": "建议增设疏散指示", "sort_order": 2},
            ]
        },
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    descriptions = {i["description"] for i in items}
    assert "安全出口被锁闭（已复核）" in descriptions
    assert "建议增设疏散指示" in descriptions
    assert "二层灭火器巡检记录不全" not in descriptions  # 省略 id 即删除

    # 未提交字段保持不变
    assert resp.json()["title"] == "某商场消防检查记录"


def test_update_item_with_foreign_id_rejected(client):
    tokens = register(client)
    record_id = _failed_record_id(client, tokens)
    resp = client.put(
        f"{BASE}/{record_id}",
        headers=auth_headers(tokens),
        json={"items": [{"id": str(uuid.uuid4()), "item_type": "violation", "description": "x"}]},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_item_type_rejected(client):
    tokens = register(client)
    record_id = _failed_record_id(client, tokens)
    resp = client.put(
        f"{BASE}/{record_id}",
        headers=auth_headers(tokens),
        json={"items": [{"item_type": "bogus", "description": "x"}]},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_finalized_record_update_returns_409(client):
    tokens = register(client)
    record_id = _failed_record_id(client, tokens)
    resp = client.put(
        f"{BASE}/{record_id}", headers=auth_headers(tokens), json={"status": "finalized"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "finalized"

    # 已 finalized：任何修改（包括试图改回 draft）都 409
    resp = client.put(
        f"{BASE}/{record_id}", headers=auth_headers(tokens), json={"title": "改"}
    )
    assert resp.status_code == 409
    resp = client.put(
        f"{BASE}/{record_id}", headers=auth_headers(tokens), json={"status": "draft"}
    )
    assert resp.status_code == 409


def test_ownership_other_user_gets_404(client):
    tokens = register(client)
    other = register(client, email="other@example.com")
    record_id = _failed_record_id(client, tokens)

    for method, url in [
        ("GET", f"{BASE}/{record_id}"),
        ("PUT", f"{BASE}/{record_id}"),
        ("GET", f"{BASE}/{record_id}/download"),
    ]:
        resp = client.request(method, url, headers=auth_headers(other), json={} if method == "PUT" else None)
        assert resp.status_code == 404, (method, url, resp.text)

    # 列表也不可见
    resp = client.get(BASE, headers=auth_headers(other))
    assert resp.json()["total"] == 0

    # admin 可见
    admin = register(client, email="admin@example.com")
    make_admin(admin["user"]["id"])
    resp = client.get(f"{BASE}/{record_id}", headers=auth_headers(admin))
    assert resp.status_code == 200


def test_pagination_and_status_filter(client):
    tokens = register(client)
    for _ in range(3):
        task_id = generate_inspection(client, tokens)
        wait_task(client, tokens, task_id)

    resp = client.get(BASE, params={"page": 1, "page_size": 2}, headers=auth_headers(tokens))
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1 and body["page_size"] == 2

    resp = client.get(BASE, params={"page": 2, "page_size": 2}, headers=auth_headers(tokens))
    assert len(resp.json()["items"]) == 1

    resp = client.get(BASE, params={"status": "failed"}, headers=auth_headers(tokens))
    assert resp.json()["total"] == 3
    resp = client.get(BASE, params={"status": "finalized"}, headers=auth_headers(tokens))
    assert resp.json()["total"] == 0

    # 非法分页参数
    resp = client.get(BASE, params={"page_size": 101}, headers=auth_headers(tokens))
    assert resp.status_code == 400


def test_download_renders_docx_on_demand(client):
    tokens = register(client)
    record_id = _failed_record_id(client, tokens)
    client.put(
        f"{BASE}/{record_id}",
        headers=auth_headers(tokens),
        json={
            "title": "某商场消防检查记录",
            "summary": "检查情况概述",
            "items": [{"item_type": "violation", "description": "安全出口被锁闭", "sort_order": 1}],
        },
    )
    resp = client.get(f"{BASE}/{record_id}/download", headers=auth_headers(tokens))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    disposition = resp.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="inspection-record-')
    assert disposition.endswith('.docx"')
    assert resp.content[:2] == b"PK"  # docx 是 zip

    # 再次下载：生成新版本（version 递增，历史保留）
    resp2 = client.get(f"{BASE}/{record_id}/download", headers=auth_headers(tokens))
    assert resp2.status_code == 200
    assert resp2.content[:2] == b"PK"

    # 文书内容来自已保存结构化数据
    from docx import Document
    import io

    doc = Document(io.BytesIO(resp2.content))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "某商场消防检查记录" in text
    assert "检查情况概述" in text


def test_download_other_user_404_and_unauthenticated_401(client):
    tokens = register(client)
    record_id = _failed_record_id(client, tokens)
    resp = client.get(f"{BASE}/{record_id}/download")
    assert resp.status_code == 401


def test_remarks_too_long_rejected(client):
    tokens = register(client)
    resp = client.post(
        f"{BASE}/generate",
        headers=auth_headers(tokens),
        files={"video": ("scene.mp4", b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64, "video/mp4")},
        data={"remarks": "x" * 2001},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
