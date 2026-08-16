"""Authentication & session tests (specs/authentication.md)."""
from __future__ import annotations


def test_health_public(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_register_login_me_flow(client):
    r = client.post("/api/auth/register", json={"email": "a@test.com", "password": "password123", "full_name": "甲"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["role"] == "inspector"  # ordinary registration cannot pick a role
    assert body["user"]["full_name"] == "甲"

    hdrs = {"Authorization": f"Bearer {body['access_token']}"}
    r = client.get("/api/auth/me", headers=hdrs)
    assert r.status_code == 200
    assert r.json()["email"] == "a@test.com"

    r = client.post("/api/auth/login", json={"email": "a@test.com", "password": "password123"})
    assert r.status_code == 200


def test_duplicate_email_conflict(client):
    payload = {"email": "dup@test.com", "password": "password123"}
    assert client.post("/api/auth/register", json=payload).status_code == 200
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT"


def test_invalid_credentials_generic(client):
    r = client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_registration_disabled(client):
    import app.core.config as config_mod

    original = config_mod.get_settings().REGISTRATION_ENABLED
    config_mod.get_settings().REGISTRATION_ENABLED = False
    try:
        r = client.post("/api/auth/register", json={"email": "x@test.com", "password": "password123"})
        assert r.status_code == 403
    finally:
        config_mod.get_settings().REGISTRATION_ENABLED = original


def test_protected_endpoint_requires_token(client):
    r = client.get("/api/tasks")
    assert r.status_code == 401
    r = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert r.status_code == 401


def test_refresh_token_flow(client):
    r = client.post("/api/auth/register", json={"email": "rf@test.com", "password": "password123"})
    refresh = r.json()["refresh_token"]
    r = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert r.json()["access_token"]
    # bad refresh token -> 401
    r = client.post("/api/auth/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401
