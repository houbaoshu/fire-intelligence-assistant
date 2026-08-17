"""任务状态机：全平台唯一的显式转移表（specs/workflow.md §9 / API.md §8）。

状态与枚举定义权在 DATABASE.md `ai_tasks` 表；本模块定义**转移模型**：

```text
                 ┌──────────┐  claim   ┌────────────┐
  (create) ────▶ │ pending  │ ───────▶ │ processing │ ──┬─▶ completed
                 └────┬─────┘          └─────┬──────┘   ├─▶ failed
                      │ cancel               │ cancel   └─▶ cancelled
                      ▼                      ▲
                 cancelled                   │ requeue（reaper 恢复卡住任务）
                      retry = 新实例（非转移，原任务保留审计）
```

规则：

- 所有 ``ai_tasks.status`` 变更必须经 ``transition()`` 校验；非法转移抛
  ``TASK_STATE_CONFLICT``（409）。worker、retry、cancel、管线回写、reaper
  统一走这一入口。
- 终态（completed/failed/cancelled）无出边：retry 语义为创建新任务实例
  （attempt_count 递增，原任务 id 记入 input_data.retry_of），而非状态回转。
- ``processing → pending`` 仅供 reaper 恢复租约过期（worker 崩溃）的卡住任务，
  actor 必须为 ``"reaper"``。
- ``queued`` 为外部队列 provider 预留；进程内执行器不入 queued 中间态。
"""

from app.core.exceptions import conflict
from app.core.logging import get_logger
from app.models.ai_task import AITask

logger = get_logger("tasks.state_machine")

#: 显式转移表：key 为源状态，value 为允许的目标状态集合。
TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"queued", "processing", "cancelled"}),
    "queued": frozenset({"processing", "cancelled"}),
    "processing": frozenset({"completed", "failed", "cancelled", "pending"}),
    "completed": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}

#: 仅 reaper 可执行的恢复性转移（processing → pending）
_REAPER_ONLY: frozenset[tuple[str, str]] = frozenset({("processing", "pending")})


def transition(task: AITask, target: str, *, actor: str, reason: str = "") -> None:
    """校验并执行状态转移。非法转移抛 409 TASK_STATE_CONFLICT。

    ``actor`` 标识发起方（worker / user / reaper / pipeline），写入日志供审计追踪。
    只修改内存中的 task，调用方负责 commit。
    """
    source = task.status
    allowed = TRANSITIONS.get(source, frozenset())
    if target not in allowed or (
        (source, target) in _REAPER_ONLY and actor != "reaper"
    ):
        raise conflict(
            "TASK_STATE_CONFLICT",
            f"任务状态不允许从 {source} 变更为 {target}",
        )
    task.status = target
    logger.info(
        "task transition: task_id=%s %s -> %s actor=%s%s",
        task.id,
        source,
        target,
        actor,
        f" reason={reason}" if reason else "",
    )
