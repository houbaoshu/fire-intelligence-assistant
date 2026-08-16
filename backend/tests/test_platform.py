"""Milestone 7: monitoring, metrics and cache."""
from __future__ import annotations


def test_metrics_endpoint(client):
    # hit a few endpoints so counters exist
    client.get("/health")
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "http_requests_total" in body  # counter suffix applied by the registry
    assert "http_request_duration_seconds" in body


def test_ttl_cache():
    from app.core.cache import ttl_cache

    calls = {"n": 0}

    @ttl_cache(seconds=30)
    def expensive():
        calls["n"] += 1
        return calls["n"]

    assert expensive() == 1
    assert expensive() == 1  # cached
    assert calls["n"] == 1
    expensive.cache_clear()
    assert expensive() == 2
