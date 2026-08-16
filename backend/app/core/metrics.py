"""Minimal Prometheus metrics registry (text exposition format).

No external dependency; production can swap in a full metrics stack
(prometheus-client / OpenTelemetry) behind the same endpoint.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from contextlib import contextmanager

_lock = threading.Lock()
_counters: dict[tuple[str, frozenset], float] = defaultdict(float)
_gauges: dict[tuple[str, frozenset], float] = defaultdict(float)
_histograms: dict[tuple[str, frozenset], list[float]] = defaultdict(list)

_DESCRIPTIONS: dict[str, str] = {}


def describe(name: str, help_text: str) -> None:
    _DESCRIPTIONS[name] = help_text


def _labels(**labels: str) -> frozenset:
    return frozenset(labels.items())


def inc_counter(name: str, value: float = 1, **labels: str) -> None:
    with _lock:
        _counters[(name, _labels(**labels))] += value


def set_gauge(name: str, value: float, **labels: str) -> None:
    with _lock:
        _gauges[(name, _labels(**labels))] = value


def observe_histogram(name: str, value: float, **labels: str) -> None:
    with _lock:
        _histograms[(name, _labels(**labels))].append(value)


@contextmanager
def timed(name: str, **labels: str):
    start = time.monotonic()
    try:
        yield
    finally:
        observe_histogram(name, time.monotonic() - start, **labels)


def _label_str(labels: frozenset) -> str:
    if not labels:
        return ""
    items = sorted(labels)
    return "{" + ",".join(f'{k}="{v}"' for k, v in items) + "}"


def _render(name: str, suffix: str, samples: dict) -> str:
    lines: list[str] = []
    help_text = _DESCRIPTIONS.get(name, "")
    if help_text:
        lines.append(f"# HELP {name}{suffix} {help_text}")
    lines.append(
        f"# TYPE {name}{suffix} counter" if suffix == "_total" else f"# TYPE {name}{suffix} gauge"
    )
    for (_, labels), value in sorted(samples.items()):
        lines.append(f"{name}{suffix}{_label_str(labels)} {value:g}")
    return "\n".join(lines)


def render_metrics() -> str:
    with _lock:
        parts = []
        for (name, labels), value in sorted(_counters.items()):
            if name not in _DESCRIPTIONS:
                continue
            parts.append(_render(name, "_total", {(name, labels): value}))
        for (name, labels), value in sorted(_gauges.items()):
            parts.append(_render(name, "", {(name, labels): value}))
        for (name, labels), samples in sorted(_histograms.items()):
            if samples:
                parts.append(f"# TYPE {name} histogram")
                parts.append(f"{name}_count {len(samples)}")
                parts.append(f"{name}_sum {sum(samples):g}")
    return "\n".join(parts) + "\n"
