"""Plugin registry: load plugins from the plugins package by entry point.

A plugin module exposes:
    PLUGIN = {"name": str, "version": str, "description": str, "hooks": {...}}

Hooks are named callables invoked by the platform at defined points
(currently: "qa_post_process" receives the QA result dict and may adjust it).
Plugins are real code executed in the backend — never client-side.
"""
from __future__ import annotations

import importlib
import pkgutil

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.aiplatform import PluginRecord

logger = get_logger("plugins")


class PluginRegistry:
    def __init__(self):
        self._modules: dict[str, object] = {}

    def discover(self) -> list[dict]:
        """Load all plugin modules under app.plugins.builtin."""
        import app.plugins.builtin as builtin_pkg

        found = []
        for mod_info in pkgutil.iter_modules(builtin_pkg.__path__):
            try:
                mod = importlib.import_module(f"app.plugins.builtin.{mod_info.name}")
                plugin = getattr(mod, "PLUGIN", None)
                if not isinstance(plugin, dict):
                    continue
                self._modules[plugin.get("name", mod_info.name)] = mod
                found.append(plugin)
            except Exception as exc:  # noqa: BLE001
                logger.warning("plugin %s load failed: %s", mod_info.name, exc)
        return found

    def run_hook(self, hook: str, payload: dict) -> dict:
        for mod in self._modules.values():
            plugin = getattr(mod, "PLUGIN", {})
            hooks = plugin.get("hooks", {})
            fn = hooks.get(hook)
            if callable(fn):
                try:
                    payload = fn(payload) or payload
                except Exception as exc:  # noqa: BLE001
                    logger.warning("plugin hook %s failed: %s", hook, exc)
        return payload


_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


class PluginService:
    def __init__(self, db: Session):
        self.db = db

    def sync_records(self) -> None:
        """Persist discovered plugins as PluginRecord rows."""
        for plugin in get_registry().discover():
            exists = self.db.scalar(select(PluginRecord).where(PluginRecord.name == plugin.get("name", "")))
            if exists is None:
                self.db.add(
                    PluginRecord(
                        name=plugin.get("name", "unnamed"),
                        version=plugin.get("version", "0.1.0"),
                        description=plugin.get("description"),
                        entry_point="builtin",
                        enabled=plugin.get("enabled", True),
                    )
                )
        self.db.commit()

    def list(self) -> list[PluginRecord]:
        return list(self.db.scalars(select(PluginRecord).order_by(PluginRecord.name)).all())
