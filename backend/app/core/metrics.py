"""Prometheus 文本格式指标（M7，无外部依赖自实现）。

- ``http_requests_total{method,route,status}``：HTTP 请求计数，路由用模板
  （如 ``/api/tasks/{task_id}``）避免高基数；未匹配路由记为 ``unmatched``。
- ``http_request_duration_seconds{method,route}``：请求耗时直方图。
- ``ai_tasks_terminal_total{task_type,status}``：任务终态计数，进程内累计，
  **进程重启清零**（非持久历史，仅供运行期观察与告警）。

由 ``main.py`` 的 HTTP middleware 采集，``/metrics`` 自身不计入。
"""

import threading

DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class Counter:
    def __init__(self, name: str, help_text: str) -> None:
        self.name = name
        self.help_text = help_text
        self._values: dict[tuple[tuple[str, str], ...], float] = {}

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        key = tuple(sorted(labels.items()))
        self._values[key] = self._values.get(key, 0.0) + amount

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} counter"]
        for label_pairs, value in sorted(self._values.items()):
            lines.append(f"{self.name}{_format_labels(label_pairs)} {_format_number(value)}")
        return "\n".join(lines)


class Histogram:
    def __init__(
        self, name: str, help_text: str, buckets: tuple[float, ...] = DEFAULT_BUCKETS
    ) -> None:
        self.name = name
        self.help_text = help_text
        self.buckets = buckets
        self._counts: dict[tuple[tuple[str, str], ...], list[int]] = {}
        self._sums: dict[tuple[tuple[str, str], ...], float] = {}

    def observe(self, value: float, **labels: str) -> None:
        key = tuple(sorted(labels.items()))
        counts = self._counts.setdefault(key, [0] * (len(self.buckets) + 1))
        for i, upper in enumerate(self.buckets):
            if value <= upper:
                counts[i] += 1
        counts[-1] += 1  # +Inf
        self._sums[key] = self._sums.get(key, 0.0) + value

    def render(self) -> str:
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} histogram",
        ]
        for label_pairs, counts in sorted(self._counts.items()):
            cumulative = 0
            for i, upper in enumerate(self.buckets):
                cumulative += counts[i]
                lines.append(
                    f"{self.name}_bucket{_format_labels(label_pairs, le=_format_number(upper))} {cumulative}"
                )
            total = cumulative + counts[-1]
            lines.append(f'{self.name}_bucket{_format_labels(label_pairs, le="+Inf")} {total}')
            lines.append(
                f"{self.name}_sum{_format_labels(label_pairs)} {_format_number(self._sums[label_pairs])}"
            )
            lines.append(f"{self.name}_count{_format_labels(label_pairs)} {total}")
        return "\n".join(lines)


def _format_labels(
    label_pairs: tuple[tuple[str, str], ...], **extra: str
) -> str:
    pairs = list(label_pairs) + sorted(extra.items())
    if not pairs:
        return ""
    inner = ",".join(f'{k}="{_escape(v)}"' for k, v in pairs)
    return "{" + inner + "}"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else repr(float(value))


class MetricsRegistry:
    """简单注册表：线程安全（锁保护渲染与写入的一致快照）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.http_requests = Counter(
            "http_requests_total", "HTTP requests by route template, method and status code."
        )
        self.http_request_duration = Histogram(
            "http_request_duration_seconds", "HTTP request latency in seconds."
        )
        self.tasks_terminal = Counter(
            "ai_tasks_terminal_total",
            "AI tasks reaching a terminal status (in-process, resets on restart).",
        )

    def record_http_request(
        self, method: str, route: str, status: int, duration_seconds: float
    ) -> None:
        labels = {"method": method, "route": route}
        with self._lock:
            self.http_requests.inc(method=method, route=route, status=str(status))
            self.http_request_duration.observe(duration_seconds, **labels)

    def record_task_terminal(self, task_type: str, status: str) -> None:
        with self._lock:
            self.tasks_terminal.inc(task_type=task_type, status=status)

    def render(self) -> str:
        with self._lock:
            sections = [
                self.http_requests.render(),
                self.http_request_duration.render(),
                self.tasks_terminal.render(),
            ]
        return "\n".join(sections) + "\n"


_registry = MetricsRegistry()


def get_metrics_registry() -> MetricsRegistry:
    return _registry
