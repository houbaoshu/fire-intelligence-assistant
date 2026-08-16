"""Structured logging setup.

Logs must never contain passwords, tokens or sensitive document content.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import get_settings

_CONFIGURED = False


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    settings = get_settings()

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"
        if False
        else "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    try:
        log_dir = settings.data_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_dir / "app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception:  # pragma: no cover - logging must not break startup
        pass

    # Keep third-party loggers reasonably quiet
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
