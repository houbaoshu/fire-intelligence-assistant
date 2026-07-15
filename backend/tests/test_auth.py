from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_checks_database_and_storage(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_register_login_and_current_user(client: TestClient) -> None:
    registration = client.post(
        "/api/auth/register",
        json={
            "email": "Inspector@Example.com",
            "password": "a-secure-password",
            "username": "Inspector",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["email"] == "inspector@example.com"
    assert registration.json()["role"] == "inspector"
    assert "password" not in registration.text

    login = client.post(
        "/api/auth/login",
        json={"email": "inspector@example.com", "password": "a-secure-password"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] != tokens["refresh_token"]

    current = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert current.status_code == 200
    assert current.json()["email"] == "inspector@example.com"


def test_authentication_errors_use_standard_envelope(client: TestClient) -> None:
    missing = client.get("/api/auth/me")
    assert missing.status_code == 401
    assert missing.json() == {
        "success": False,
        "error": {
            "code": "AUTHENTICATION_REQUIRED",
            "message": "Authentication is required.",
            "details": None,
        },
    }

    invalid = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "wrong"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_registration_validates_password_and_duplicates(client: TestClient) -> None:
    weak = client.post(
        "/api/auth/register",
        json={"email": "inspector@example.com", "password": "short"},
    )
    assert weak.status_code == 422
    assert weak.json()["error"]["code"] == "VALIDATION_ERROR"

    payload = {"email": "inspector@example.com", "password": "a-secure-password"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
