"""进程内 TTL 缓存（M7）。

- 线程安全（threading.Lock）；接口（get/set/invalidate_prefix）保持最小，
  后续可平滑替换为 Redis 实现同一抽象。
- 进程内缓存重启即清空；多实例部署时各实例独立缓存，TTL 兜底一致性。
"""

import threading
import time


class TTLCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[float, object]] = {}

    def get(self, key: str) -> object | None:
        """命中且未过期返回缓存值，否则返回 None（并顺手清除过期项）。"""
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= now:
                del self._entries[key]
                return None
            return value

    def set(self, key: str, value: object, ttl_seconds: float) -> None:
        with self._lock:
            self._entries[key] = (time.monotonic() + ttl_seconds, value)

    def invalidate_prefix(self, prefix: str) -> int:
        """按前缀失效（如记录/知识库变更后失效 statistics:/knowledge: 分组）。"""
        with self._lock:
            keys = [k for k in self._entries if k.startswith(prefix)]
            for key in keys:
                del self._entries[key]
        return len(keys)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_cache = TTLCache()

#: 缓存键前缀约定：统计聚合与知识库状态
PREFIX_STATISTICS = "statistics:"
PREFIX_KNOWLEDGE_STATUS = "knowledge:status"


def get_cache() -> TTLCache:
    return _cache


def invalidate_read_models() -> None:
    """业务数据（记录/知识库/任务终态）变更后统一失效只读聚合缓存。"""
    _cache.invalidate_prefix(PREFIX_STATISTICS)
    _cache.invalidate_prefix(PREFIX_KNOWLEDGE_STATUS)
