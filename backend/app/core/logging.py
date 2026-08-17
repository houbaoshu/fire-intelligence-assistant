"""结构化日志配置。

约定：
- 通过 ``set_request_id`` 在中间件中绑定请求级 request_id。
- 禁止记录密码、token、API key 与敏感文档内容。
"""

import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str) -> None:
    _request_id.set(request_id)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        parts = [
            f"timestamp={datetime.now(timezone.utc).isoformat()}",
            f"level={record.levelname}",
            f"request_id={getattr(record, 'request_id', '-')}",
            f"module={record.module}",
            f"message={record.getMessage()}",
        ]
        if record.exc_info:
            parts.append(f"exception={self.formatException(record.exc_info)}")
        return " ".join(parts)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_RequestIdFilter())

    root = logging.getLogger("app")
    root.setLevel(level)
    root.handlers = [handler]
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"app.{name}")
