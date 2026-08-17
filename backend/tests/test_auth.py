"""认证端点测试（API.md §2 契约）。"""

import uuid

USER = {"email": "tester@example.com", "password": "password123", "full_name": "张三"}


def _register(client, **overrides) -> dict:
    payload = {**USER, **overrides}
    return client.post("/api/auth/register", json=payload)


def test_register_returns_tokens_and_user(client):
    resp = _register(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    user = body["user"]
    assert uuid.UUID(user["id"])  # id 为 UUID
    assert user["email"] == USER["email"]
    assert user["full_name"] == USER["full_name"]
    assert user["role"] == "inspector"  # 默认角色


def test_register_duplicate_email_returns_409(client):
    assert _register(client).status_code == 200
    resp = _register(client)
    assert resp.status_code == 409
    body = resp.json()
    assert body["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert body["error"]["message"]


def test_register_invalid_payload_returns_400(client):
    resp = client.post("/api/auth/register", json={"email": "not-an-email"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_success(client):
    _register(client)
    resp = client.post(
        "/api/auth/login", json={"email": USER["email"], "password": USER["password"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == USER["email"]


def test_login_wrong_password_returns_401(client):
    _register(client)
    resp = client.post(
        "/api/auth/login", json={"email": USER["email"], "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_unknown_email_returns_same_401(client):
    """登录失败信息不区分邮箱不存在与密码错误（防账号枚举）。"""
    _register(client)
    unknown = client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": "x" * 8}
    )
    wrong_pw = client.post(
        "/api/auth/login", json={"email": USER["email"], "password": "wrong-pass"}
    )
    assert unknown.status_code == wrong_pw.status_code == 401
    assert unknown.json() == wrong_pw.json()


def test_me_with_valid_token(client):
    tokens = _register(client).json()
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == USER["email"]
    assert body["full_name"] == USER["full_name"]
    assert set(body.keys()) == {"id", "email", "full_name", "role"}


def test_me_without_token_returns_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_with_refresh_token_rejected(client):
    """refresh token 不能当作 access token 使用。"""
    tokens = _register(client).json()
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert resp.status_code == 401


def test_refresh_returns_new_access_token(client):
    tokens = _register(client).json()
    resp = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200


def test_refresh_with_access_token_rejected(client):
    tokens = _register(client).json()
    resp = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_refresh_with_garbage_token_rejected(client):
    resp = client.post("/api/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert resp.status_code == 401
