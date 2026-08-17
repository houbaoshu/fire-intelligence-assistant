"""Statistics 测试（API.md §7）：形状、scope、by_status 只含有数据的键。"""

from .helpers import auth_headers, generate_inspection, make_admin, register, wait_task


def test_statistics_empty_personal_scope(client):
    tokens = register(client)
    resp = client.get("/api/statistics", headers=auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "personal"
    assert body["generated_at"]
    assert body["records"]["inspection_records"] == {"total": 0, "by_status": {}}
    assert body["records"]["photo_reports"] == {"total": 0, "by_status": {}}
    assert body["records"]["interview_records"] == {"total": 0, "by_status": {}}
    assert body["tasks"] == {"total": 0, "by_status": {}}
    # M2：knowledge_documents 表 M3 落地，此处为全 0 结构
    assert body["knowledge"] == {
        "document_count": 0,
        "indexed_count": 0,
        "indexing_count": 0,
        "failed_count": 0,
    }
    assert body["generated_documents"] == {"total": 0}


def test_statistics_counts_after_activity(client):
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)

    record_id = client.get(
        "/api/inspection-record", headers=auth_headers(tokens)
    ).json()["items"][0]["id"]
    client.put(
        f"/api/inspection-record/{record_id}",
        headers=auth_headers(tokens),
        json={"title": "t", "status": "draft"},
    )
    client.get(
        f"/api/inspection-record/{record_id}/download", headers=auth_headers(tokens)
    )

    body = client.get("/api/statistics", headers=auth_headers(tokens)).json()
    assert body["records"]["inspection_records"]["total"] == 1
    assert body["records"]["inspection_records"]["by_status"] == {"draft": 1}
    assert body["tasks"]["total"] == 1
    assert body["tasks"]["by_status"] == {"failed": 1}
    assert body["generated_documents"]["total"] == 1


def test_statistics_scoped_to_owner(client):
    tokens = register(client)
    other = register(client, email="other@example.com")
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)

    body = client.get("/api/statistics", headers=auth_headers(other)).json()
    assert body["records"]["inspection_records"]["total"] == 0
    assert body["tasks"]["total"] == 0

    admin = register(client, email="admin@example.com")
    make_admin(admin["user"]["id"])
    body = client.get("/api/statistics", headers=auth_headers(admin)).json()
    assert body["scope"] == "system"
    assert body["records"]["inspection_records"]["total"] == 1
    assert body["tasks"]["total"] == 1


def test_statistics_requires_auth(client):
    resp = client.get("/api/statistics")
    assert resp.status_code == 401
