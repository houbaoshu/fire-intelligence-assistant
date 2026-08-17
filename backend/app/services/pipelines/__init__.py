"""生成管线（M4 已接入真实 AI 能力）。

每条管线定义：所需 AI 能力、阶段序列（阶段名写入 ai_tasks.current_stage）、
阶段执行入口。能力未配置时任务以可读错误 AI_SERVICE_NOT_CONFIGURED 失败，
绝不编造结构化结果。

实现要点：
1. 各能力 client 在 ``app/services/ai/``（OpenAI 兼容 API）。
2. 各管线子类的 ``execute_stage`` 按阶段调用对应能力 service，
   中间产物存入 ``ctx.artifacts``（帧、OCR 文本、transcript 等）。
3. 最后一个阶段（draft）返回 ``PipelineResult``：``fields`` 为业务记录的列更新，
   ``items`` / ``images`` 为子记录列表（见 tasks/worker.py 的应用逻辑）。
4. LLM 输出一律为结构化 JSON，解析失败按任务失败处理；
   无依据字段留空，禁止编造。
5. 部分失败（单帧分析失败等）降级并写入 ``PipelineResult.warnings``
   （落库到 ai_tasks.result_data.warnings），不静默丢弃。
"""

from app.services.pipelines.base import (
    PipelineContext,
    PipelineError,
    PipelineResult,
    TaskCancelled,
)
from app.services.pipelines.generation import PIPELINES

__all__ = [
    "PIPELINES",
    "PipelineContext",
    "PipelineError",
    "PipelineResult",
    "TaskCancelled",
]
