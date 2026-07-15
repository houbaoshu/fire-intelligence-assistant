from __future__ import annotations

import sys
import time

import pytest
from fastapi.testclient import TestClient

from app.services.ai import media


def auth_headers(client: TestClient) -> dict[str, str]:
    registration = client.post(
        "/api/auth/register",
        json={"email": "business@example.com", "password": "a-secure-password"},
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"email": "business@example.com", "password": "a-secure-password"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def wait_for_terminal(
    client: TestClient, task_id: str, headers: dict[str, str]
) -> dict[str, object]:
    for _ in range(50):
        response = client.get(f"/api/tasks/{task_id}", headers=headers)
        assert response.status_code == 200
        task = response.json()
        if task["status"] in {"completed", "failed", "cancelled"}:
            return task
        time.sleep(0.02)
    raise AssertionError("task did not reach a terminal state")


def test_generation_creates_durable_task_and_safe_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(media, "_ffmpeg", lambda: sys.executable)
    headers = auth_headers(client)
    response = client.post(
        "/api/inspection-record/generate",
        headers=headers,
        files={"video": ("inspection.mp4", b"not-a-real-video", "video/mp4")},
        data={"remarks": "Only user-provided evidence may be used."},
    )
    assert response.status_code == 202
    identifiers = response.json()
    task = wait_for_terminal(client, identifiers["task_id"], headers)
    assert task["status"] == "failed"
    assert task["error_code"] == "FRAME_EXTRACTION_FAILED"
    assert "not-a-real-video" not in str(task)

    record = client.get(f"/api/inspection-record/{identifiers['entity_id']}", headers=headers)
    assert record.status_code == 200
    assert record.json()["status"] == "failed"


def test_statistics_and_task_list_are_real_and_scoped(client: TestClient) -> None:
    headers = auth_headers(client)
    statistics = client.get("/api/statistics", headers=headers)
    assert statistics.status_code == 200
    payload = statistics.json()
    assert payload["scope"] == "personal"
    assert payload["timezone"] == "UTC"
    assert all(metric["value"] >= 0 for metric in payload["metrics"])

    tasks = client.get("/api/tasks", headers=headers)
    assert tasks.status_code == 200
    assert tasks.json() == {"items": [], "total": 0}


def test_interview_requires_exactly_one_media_file(client: TestClient) -> None:
    headers = auth_headers(client)
    missing = client.post("/api/interview-record/generate", headers=headers)
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "ONE_MEDIA_FILE_REQUIRED"

    both = client.post(
        "/api/interview-record/generate",
        headers=headers,
        files={
            "audio": ("interview.mp3", b"audio", "audio/mpeg"),
            "video": ("interview.mp4", b"video", "video/mp4"),
        },
    )
    assert both.status_code == 422
    assert both.json()["error"]["code"] == "ONE_MEDIA_FILE_REQUIRED"


def test_inspector_cannot_manage_knowledge_documents(client: TestClient) -> None:
    headers = auth_headers(client)
    response = client.post(
        "/api/knowledge/documents",
        headers=headers,
        files={"file": ("regulation.pdf", b"pdf", "application/pdf")},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
