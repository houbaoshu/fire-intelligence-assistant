"""插件契约与钩子执行器（M8）。

``run_hook`` 从 plugins 表读取启用状态（DB 为唯一事实来源），仅执行
启用插件在对应钩子点注册的回调；回调接收可变上下文 dict，可就地修改
（如 on_qa_answer 改写 answer）。任何钩子异常降级为 warning 日志。
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger("plugins")

# 平台定义的钩子执行点
HOOK_POINTS = ("on_task_terminal", "on_qa_answer")

# 钩子回调签名：接收可变上下文 dict，返回值忽略
HookFunc = Callable[[dict], None]


@dataclass(frozen=True)
class Plugin:
    """插件契约：内置插件模块以模块级 ``PLUGIN`` 常量提供。"""

    name: str
    version: str
    description: str
    hooks: dict[str, HookFunc] = field(default_factory=dict)


def builtin_plugins() -> list[Plugin]:
    """内置插件清单（延迟导入，避免与模型层循环依赖）。"""
    from app.plugins.builtin import qa_disclaimer, task_terminal_logger

    return [task_terminal_logger.PLUGIN, qa_disclaimer.PLUGIN]


def _enabled_names(session: Session) -> set[str]:
    from app.models.ai_platform import Plugin as PluginRow

    stmt = select(PluginRow.name).where(PluginRow.enabled.is_(True))
    return set(session.execute(stmt).scalars().all())


def run_hook(session: Session, hook_name: str, context: dict) -> dict:
    """在指定钩子点执行全部启用插件的回调；返回（可能被修改的）上下文。"""
    if hook_name not in HOOK_POINTS:
        raise ValueError(f"未知钩子点: {hook_name}")
    try:
        enabled = _enabled_names(session)
    except SQLAlchemyError as exc:
        logger.info("插件启用状态查询失败，跳过钩子 %s: %s", hook_name, type(exc).__name__)
        return context
    for plugin in builtin_plugins():
        if plugin.name not in enabled:
            continue
        hook = plugin.hooks.get(hook_name)
        if hook is None:
            continue
        try:
            hook(context)
        except Exception as exc:  # 钩子失败绝不阻断主流程
            logger.warning(
                "插件 %s 钩子 %s 执行失败: %s",
                plugin.name, hook_name, type(exc).__name__,
            )
    return context
