"""企业管理测试（API.md §11）：权限种子、矩阵读写与保护、组织/部门 CRUD、
用户管理、审计查询、supervisor 组织范围、非 admin 403。"""

import uuid

from app.db import SessionLocal
from app.models.organization import Permission, RolePermission
from app.services.permission_service import PERMISSION_CODES, PermissionService

from .helpers import auth_headers, generate_inspection, make_admin, make_role, register, wait_task

ADMIN_BASE = "/api/admin"


def _register_admin(client, email="admin@example.com"):
    tokens = register(client, email=email)
    make_admin(tokens["user"]["id"])
    return tokens


def _create_org(client, admin, code="FD-001", name="某市消防救援支队"):
    resp = client.post(
        f"{ADMIN_BASE}/organizations",
        headers=auth_headers(admin),
        json={"name": name, "code": code, "description": "描述"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------- 权限种子与 me.permissions ----------


def test_permission_seed_idempotent(client):
    session = SessionLocal()
    try:
        before_p = session.query(Permission).count()
        before_rp = session.query(RolePermission).count()
        assert before_p == len(PERMISSION_CODES)
        PermissionService(session).seed()
        session.commit()
        assert session.query(Permission).count() == before_p
        assert session.query(RolePermission).count() == before_rp
    finally:
        session.close()


def test_me_returns_permissions_for_admin(client):
    admin = _register_admin(client)
    body = client.get("/api/auth/me", headers=auth_headers(admin)).json()
    assert set(body["permissions"]) == set(PERMISSION_CODES)


# ---------- 非 admin 访问 admin 端点 403 ----------


def test_admin_endpoints_forbidden_for_non_admin(client):
    tokens = register(client)
    for method, url in [
        ("GET", f"{ADMIN_BASE}/organizations"),
        ("POST", f"{ADMIN_BASE}/organizations"),
        ("GET", f"{ADMIN_BASE}/departments"),
        ("GET", f"{ADMIN_BASE}/users"),
        ("GET", f"{ADMIN_BASE}/permissions"),
        ("GET", f"{ADMIN_BASE}/audit-logs"),
    ]:
        resp = client.request(method, url, headers=auth_headers(tokens), json={})
        assert resp.status_code == 403, (method, url, resp.text)
        assert resp.json()["error"]["code"] == "FORBIDDEN"


# ---------- 组织 CRUD ----------


def test_organization_crud_and_code_conflict(client):
    admin = _register_admin(client)
    org = _create_org(client, admin)
    assert org["code"] == "FD-001"
    assert org["created_at"] and org["updated_at"]

    # code 重复 409
    resp = client.post(
        f"{ADMIN_BASE}/organizations",
        headers=auth_headers(admin),
        json={"name": "另一个组织", "code": "FD-001"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ORGANIZATION_CODE_EXISTS"

    # 更新
    resp = client.put(
        f"{ADMIN_BASE}/organizations/{org['id']}",
        headers=auth_headers(admin),
        json={"name": "改名支队"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "改名支队"
    assert resp.json()["code"] == "FD-001"

    # 列表分页信封
    resp = client.get(f"{ADMIN_BASE}/organizations", headers=auth_headers(admin))
    body = resp.json()
    assert body["total"] == 1 and body["page"] == 1 and body["page_size"] == 20
    assert body["items"][0]["name"] == "改名支队"

    # 删除
    resp = client.delete(
        f"{ADMIN_BASE}/organizations/{org['id']}", headers=auth_headers(admin)
    )
    assert resp.status_code == 200
    assert resp.json() == {"id": org["id"], "deleted": True}
    assert client.get(f"{ADMIN_BASE}/organizations", headers=auth_headers(admin)).json()["total"] == 0


def test_organization_delete_with_users_409(client):
    admin = _register_admin(client)
    org = _create_org(client, admin)
    user = register(client, email="member@example.com")
    resp = client.put(
        f"{ADMIN_BASE}/users/{user['user']['id']}",
        headers=auth_headers(admin),
        json={"organization_id": org["id"]},
    )
    assert resp.status_code == 200, resp.text
    resp = client.delete(
        f"{ADMIN_BASE}/organizations/{org['id']}", headers=auth_headers(admin)
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ORGANIZATION_HAS_USERS"


def test_organization_not_found(client):
    admin = _register_admin(client)
    missing = str(uuid.uuid4())
    assert client.put(
        f"{ADMIN_BASE}/organizations/{missing}",
        headers=auth_headers(admin),
        json={"name": "x"},
    ).status_code == 404
    assert client.delete(
        f"{ADMIN_BASE}/organizations/{missing}", headers=auth_headers(admin)
    ).status_code == 404


# ---------- 部门 CRUD ----------


def test_department_crud_and_filters(client):
    admin = _register_admin(client)
    org = _create_org(client, admin)
    org2 = _create_org(client, admin, code="FD-002", name="另一支队")

    resp = client.post(
        f"{ADMIN_BASE}/departments",
        headers=auth_headers(admin),
        json={"organization_id": org["id"], "name": "防火监督科"},
    )
    assert resp.status_code == 200, resp.text
    dept = resp.json()
    assert dept["organization_id"] == org["id"] and dept["parent_id"] is None

    # 子部门
    resp = client.post(
        f"{ADMIN_BASE}/departments",
        headers=auth_headers(admin),
        json={"organization_id": org["id"], "name": "一中队", "parent_id": dept["id"]},
    )
    assert resp.status_code == 200, resp.text

    # parent 不属于同一组织 → 400
    resp = client.post(
        f"{ADMIN_BASE}/departments",
        headers=auth_headers(admin),
        json={"organization_id": org2["id"], "name": "错配", "parent_id": dept["id"]},
    )
    assert resp.status_code == 400

    # organization_id 不存在 → 400
    resp = client.post(
        f"{ADMIN_BASE}/departments",
        headers=auth_headers(admin),
        json={"organization_id": str(uuid.uuid4()), "name": "无组织"},
    )
    assert resp.status_code == 400

    # 按 organization_id 过滤
    body = client.get(
        f"{ADMIN_BASE}/departments",
        params={"organization_id": org["id"]},
        headers=auth_headers(admin),
    ).json()
    assert body["total"] == 2

    # 更新
    resp = client.put(
        f"{ADMIN_BASE}/departments/{dept['id']}",
        headers=auth_headers(admin),
        json={"name": "防火监督大队"},
    )
    assert resp.status_code == 200 and resp.json()["name"] == "防火监督大队"

    # parent 指向自身 → 400
    resp = client.put(
        f"{ADMIN_BASE}/departments/{dept['id']}",
        headers=auth_headers(admin),
        json={"parent_id": dept["id"]},
    )
    assert resp.status_code == 400

    # 删除
    resp = client.delete(
        f"{ADMIN_BASE}/departments/{dept['id']}", headers=auth_headers(admin)
    )
    assert resp.status_code == 200 and resp.json()["deleted"] is True


def test_department_delete_with_users_409(client):
    admin = _register_admin(client)
    org = _create_org(client, admin)
    dept = client.post(
        f"{ADMIN_BASE}/departments",
        headers=auth_headers(admin),
        json={"organization_id": org["id"], "name": "防火监督科"},
    ).json()
    user = register(client, email="member@example.com")
    resp = client.put(
        f"{ADMIN_BASE}/users/{user['user']['id']}",
        headers=auth_headers(admin),
        json={"organization_id": org["id"], "department_id": dept["id"]},
    )
    assert resp.status_code == 200, resp.text
    resp = client.delete(
        f"{ADMIN_BASE}/departments/{dept['id']}", headers=auth_headers(admin)
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DEPARTMENT_HAS_USERS"


# ---------- 用户管理 ----------


def test_user_list_and_update(client):
    admin = _register_admin(client)
    user = register(client, email="member@example.com", full_name="李四")

    body = client.get(f"{ADMIN_BASE}/users", headers=auth_headers(admin)).json()
    assert body["total"] == 2
    item = next(i for i in body["items"] if i["email"] == "member@example.com")
    assert item["full_name"] == "李四"
    assert item["role"] == "inspector"
    assert item["is_active"] is True
    assert item["organization_id"] is None

    # 改角色与停用
    resp = client.put(
        f"{ADMIN_BASE}/users/{user['user']['id']}",
        headers=auth_headers(admin),
        json={"role": "supervisor", "is_active": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "supervisor"
    assert resp.json()["is_active"] is False

    # role 过滤
    body = client.get(
        f"{ADMIN_BASE}/users", params={"role": "supervisor"}, headers=auth_headers(admin)
    ).json()
    assert body["total"] == 1

    # 非法角色 400
    resp = client.put(
        f"{ADMIN_BASE}/users/{user['user']['id']}",
        headers=auth_headers(admin),
        json={"role": "root"},
    )
    assert resp.status_code == 400

    # 用户不存在 404
    resp = client.put(
        f"{ADMIN_BASE}/users/{uuid.uuid4()}",
        headers=auth_headers(admin),
        json={"role": "viewer"},
    )
    assert resp.status_code == 404


def test_user_self_lockout_forbidden(client):
    admin = _register_admin(client)
    admin_id = admin["user"]["id"]

    resp = client.put(
        f"{ADMIN_BASE}/users/{admin_id}",
        headers=auth_headers(admin),
        json={"is_active": False},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "SELF_LOCKOUT_FORBIDDEN"

    resp = client.put(
        f"{ADMIN_BASE}/users/{admin_id}",
        headers=auth_headers(admin),
        json={"role": "viewer"},
    )
    assert resp.status_code == 409

    # 但允许管理员修改自己的组织归属
    org = _create_org(client, admin)
    resp = client.put(
        f"{ADMIN_BASE}/users/{admin_id}",
        headers=auth_headers(admin),
        json={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    assert resp.json()["organization_id"] == org["id"]


def test_user_department_must_match_organization(client):
    admin = _register_admin(client)
    org = _create_org(client, admin)
    org2 = _create_org(client, admin, code="FD-002", name="另一支队")
    dept = client.post(
        f"{ADMIN_BASE}/departments",
        headers=auth_headers(admin),
        json={"organization_id": org["id"], "name": "防火监督科"},
    ).json()
    user = register(client, email="member@example.com")

    # 部门属于 org，但用户组织为 org2 → 400
    resp = client.put(
        f"{ADMIN_BASE}/users/{user['user']['id']}",
        headers=auth_headers(admin),
        json={"organization_id": org2["id"], "department_id": dept["id"]},
    )
    assert resp.status_code == 400

    # 部门存在但用户无组织 → 400
    resp = client.put(
        f"{ADMIN_BASE}/users/{user['user']['id']}",
        headers=auth_headers(admin),
        json={"department_id": dept["id"]},
    )
    assert resp.status_code == 400

    # 一致 → 200；再显式清除归属
    resp = client.put(
        f"{ADMIN_BASE}/users/{user['user']['id']}",
        headers=auth_headers(admin),
        json={"organization_id": org["id"], "department_id": dept["id"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["department_id"] == dept["id"]
    resp = client.put(
        f"{ADMIN_BASE}/users/{user['user']['id']}",
        headers=auth_headers(admin),
        json={"organization_id": None, "department_id": None},
    )
    assert resp.status_code == 200
    assert resp.json()["organization_id"] is None


# ---------- 权限矩阵 ----------


def test_permission_matrix_read_write(client):
    admin = _register_admin(client)

    body = client.get(f"{ADMIN_BASE}/permissions", headers=auth_headers(admin)).json()
    codes = {p["code"] for p in body["permissions"]}
    assert codes == set(PERMISSION_CODES)
    assert set(body["matrix"].keys()) == {"admin", "supervisor", "inspector", "viewer"}
    assert "record.create" in body["matrix"]["inspector"]
    assert "record.create" not in body["matrix"]["viewer"]

    # 整体替换 viewer 权限
    resp = client.put(
        f"{ADMIN_BASE}/permissions/viewer",
        headers=auth_headers(admin),
        json={"permission_codes": ["record.read"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"role": "viewer", "permission_codes": ["record.read"]}

    # 生效矩阵即时更新：viewer 的 me 不再含 knowledge.read
    viewer = register(client, email="viewer@example.com")
    make_role(viewer["user"]["id"], "viewer")
    body = client.get("/api/auth/me", headers=auth_headers(viewer)).json()
    assert body["permissions"] == ["record.read"]

    # 未知权限码 400
    resp = client.put(
        f"{ADMIN_BASE}/permissions/viewer",
        headers=auth_headers(admin),
        json={"permission_codes": ["record.read", "no.such"]},
    )
    assert resp.status_code == 400

    # 非法角色 400
    resp = client.put(
        f"{ADMIN_BASE}/permissions/root",
        headers=auth_headers(admin),
        json={"permission_codes": []},
    )
    assert resp.status_code == 400


def test_permission_matrix_admin_lockout_protected(client):
    admin = _register_admin(client)
    resp = client.put(
        f"{ADMIN_BASE}/permissions/admin",
        headers=auth_headers(admin),
        json={"permission_codes": ["record.read", "admin.users"]},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ADMIN_PERMISSION_LOCKED"


def test_matrix_change_tightens_enforcement(client):
    """矩阵调整即时生效：移除 inspector 的 record.create 后 generate 返回 403。"""
    admin = _register_admin(client)
    inspector = register(client, email="inspector@example.com")
    resp = client.put(
        f"{ADMIN_BASE}/permissions/inspector",
        headers=auth_headers(admin),
        json={"permission_codes": ["record.read", "knowledge.read", "statistics.read"]},
    )
    assert resp.status_code == 200
    resp = client.post(
        "/api/inspection-record/generate",
        headers=auth_headers(inspector),
        files={"video": ("scene.mp4", b"\x00" * 32, "video/mp4")},
    )
    assert resp.status_code == 403


def test_viewer_cannot_generate_or_finalize(client):
    """默认矩阵收紧：viewer 只读，不能创建记录（specs/_common.md）。"""
    viewer = register(client)
    make_role(viewer["user"]["id"], "viewer")
    resp = client.post(
        "/api/inspection-record/generate",
        headers=auth_headers(viewer),
        files={"video": ("scene.mp4", b"\x00" * 32, "video/mp4")},
    )
    assert resp.status_code == 403


def test_inspector_cannot_finalize(client):
    """inspector 无 record.finalize 权限，定稿返回 403。"""
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)
    record_id = client.get(
        "/api/inspection-record", headers=auth_headers(tokens)
    ).json()["items"][0]["id"]
    resp = client.put(
        f"/api/inspection-record/{record_id}",
        headers=auth_headers(tokens),
        json={"status": "finalized"},
    )
    assert resp.status_code == 403


# ---------- 审计日志 ----------


def test_audit_logs_query_and_filters(client):
    admin = _register_admin(client)
    org = _create_org(client, admin)

    body = client.get(f"{ADMIN_BASE}/audit-logs", headers=auth_headers(admin)).json()
    assert body["total"] >= 1
    first = body["items"][0]
    assert first["action"] == "admin.organization.create"
    assert first["entity_type"] == "organization"
    assert first["entity_id"] == org["id"]
    assert first["user_id"] == admin["user"]["id"]
    assert first["request_id"]

    # action 过滤
    body = client.get(
        f"{ADMIN_BASE}/audit-logs",
        params={"action": "admin.organization.create"},
        headers=auth_headers(admin),
    ).json()
    assert all(i["action"] == "admin.organization.create" for i in body["items"])

    # entity_type 过滤（无匹配）
    body = client.get(
        f"{ADMIN_BASE}/audit-logs",
        params={"entity_type": "department"},
        headers=auth_headers(admin),
    ).json()
    assert body["total"] == 0

    # user_id 过滤
    body = client.get(
        f"{ADMIN_BASE}/audit-logs",
        params={"user_id": admin["user"]["id"]},
        headers=auth_headers(admin),
    ).json()
    assert body["total"] >= 1


# ---------- supervisor 组织范围 ----------


def test_supervisor_organization_scope(client):
    admin = _register_admin(client)
    org = _create_org(client, admin)

    inspector = register(client, email="inspector@example.com")
    outsider = register(client, email="outsider@example.com")
    supervisor = register(client, email="supervisor@example.com")
    make_role(supervisor["user"]["id"], "supervisor")

    # 划入组织：inspector 与 supervisor 同组织；outsider 无组织
    for uid in (inspector["user"]["id"], supervisor["user"]["id"]):
        resp = client.put(
            f"{ADMIN_BASE}/users/{uid}",
            headers=auth_headers(admin),
            json={"organization_id": org["id"]},
        )
        assert resp.status_code == 200, resp.text

    # inspector 与 outsider 各生成一条记录
    task_id = generate_inspection(client, inspector)
    wait_task(client, inspector, task_id)
    task_id_out = generate_inspection(client, outsider)
    wait_task(client, outsider, task_id_out)

    headers = auth_headers(supervisor)

    # 统计：organization 范围，仅含同组织成员的记录/任务
    body = client.get("/api/statistics", headers=headers).json()
    assert body["scope"] == "organization"
    assert body["records"]["inspection_records"]["total"] == 1
    assert body["tasks"]["total"] == 1

    # 记录可见性：列表只见同组织记录
    body = client.get("/api/inspection-record", headers=headers).json()
    assert body["total"] == 1
    record_id = body["items"][0]["id"]

    # 详情可见；审阅他人记录（record.review）与定稿（record.finalize）放行
    assert client.get(f"/api/inspection-record/{record_id}", headers=headers).status_code == 200
    resp = client.put(
        f"/api/inspection-record/{record_id}",
        headers=headers,
        json={"status": "finalized"},
    )
    assert resp.status_code == 200, resp.text

    # 组织外记录不可见
    outsider_record_id = client.get(
        "/api/inspection-record", headers=auth_headers(outsider)
    ).json()["items"][0]["id"]
    assert (
        client.get(f"/api/inspection-record/{outsider_record_id}", headers=headers).status_code
        == 404
    )


def test_supervisor_without_organization_sees_all_statistics(client):
    supervisor = register(client, email="supervisor@example.com")
    make_role(supervisor["user"]["id"], "supervisor")
    inspector = register(client, email="inspector@example.com")
    task_id = generate_inspection(client, inspector)
    wait_task(client, inspector, task_id)

    body = client.get("/api/statistics", headers=auth_headers(supervisor)).json()
    # 未分配组织的 supervisor 默认查看全部（DATABASE.md 统计范围规则）
    assert body["scope"] == "system"
    assert body["records"]["inspection_records"]["total"] == 1
