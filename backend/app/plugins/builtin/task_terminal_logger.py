"""内置插件：任务终态日志（on_task_terminal）。

任务进入终态（completed/failed/cancelled）后记录一条结构化日志，
便于审计与问题排查。不修改任何数据。
"""

from app.core.logging import get_logger
from app.plugins.registry import Plugin

logger = get_logger("plugins.task_terminal_logger")


def _on_task_terminal(context: dict) -> None:
    logger.info(
        "任务到达终态: task_id=%s type=%s status=%s error=%s",
        context.get("task_id"),
        context.get("task_type"),
        context.get("status"),
        context.get("error_message") or "-",
    )


PLUGIN = Plugin(
    name="task_terminal_logger",
    version="1.0.0",
    description="任务进入终态时记录结构化日志（on_task_terminal）",
    hooks={"on_task_terminal": _on_task_terminal},
)
