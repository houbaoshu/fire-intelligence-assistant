"""生成管线骨架（M2）。

每条管线定义：所需 AI 能力、阶段序列（阶段名写入 ai_tasks.current_stage）、
阶段执行入口。M2 阶段 AI provider 未实现：能力未配置时任务以可读错误失败；
即使配置了密钥，阶段执行也以 AI_PROVIDER_NOT_IMPLEMENTED 失败 —— 禁止假 AI。

M4 实现者指南：
1. 在 ``app/services/ai/`` 补充各能力的真实 client（OpenAI 兼容 API）。
2. 在各管线子类中重写 ``execute_stage``：按阶段调用对应能力 service，
   产出结构化中间结果存入 ``ctx.artifacts``（帧、OCR 文本、transcript 等）。
3. 最后一个阶段（draft）返回 ``PipelineResult``：``fields`` 为业务记录的列更新，
   ``items`` / ``images`` 为子记录列表（见 tasks/worker.py 的应用逻辑）。
4. 禁止编造结构化结果：无依据字段留空。
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
