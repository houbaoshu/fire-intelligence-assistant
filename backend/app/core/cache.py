"""Small TTL cache helper (in-process; production may swap to Redis)."""
from __future__ import annotations

import threading
import time
from functools import wraps
from typing import Any, Callable


def ttl_cache(seconds: float):
    """Cache a callable's result per argument tuple for the given TTL."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        lock = threading.Lock()
        cache: dict[tuple, tuple[Any, float]] = {}

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            with lock:
                hit = cache.get(key)
                if hit is not None and now - hit[1] < seconds:
                    return hit[0]
            value = fn(*args, **kwargs)
            with lock:
                cache[key] = (value, now)
            return value

        wrapper.cache_clear = lambda: cache.clear()  # type: ignore[attr-defined]
        return wrapper

    return decorator
