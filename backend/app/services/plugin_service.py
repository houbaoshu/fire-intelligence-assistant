"""插件管理（M8，API.md §12.4）：内置插件幂等注册、列表与启停。

entry_point 记录插件模块路径（如 ``app.plugins.builtin.qa_disclaimer``）；
启用状态以 plugins 表为唯一事实来源，禁用即不执行（见 app/plugins/registry.py）。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.models.ai_platform import Plugin as PluginRow
from app.plugins.registry import builtin_plugins


class PluginService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def register_builtin(self) -> None:
        """幂等注册内置插件：name 不存在时插入（默认启用）；已存在则不覆盖
        管理员的启停选择与展示信息。"""
        existing = set(self.session.execute(select(PluginRow.name)).scalars().all())
        for plugin in builtin_plugins():
            if plugin.name in existing:
                continue
            self.session.add(
                PluginRow(
                    name=plugin.name,
                    version=plugin.version,
                    description=plugin.description,
                    entry_point=f"app.plugins.builtin.{plugin.name}",
                    enabled=True,
                )
            )
        self.session.flush()

    def list(self) -> list[PluginRow]:
        stmt = select(PluginRow).order_by(PluginRow.name)
        return list(self.session.execute(stmt).scalars().all())

    def set_enabled(self, plugin_id: uuid.UUID, enabled: bool) -> PluginRow:
        row = self.session.get(PluginRow, plugin_id)
        if row is None:
            raise not_found("插件不存在")
        row.enabled = enabled
        self.session.commit()
        self.session.refresh(row)
        return row
