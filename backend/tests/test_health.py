"""Smoke tests for the FastAPI application."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    """The health endpoint reports that the API is available."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
