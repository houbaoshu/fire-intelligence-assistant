"""生成管线基类与共享类型。扩展约定见 app/services/pipelines/__init__.py。"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from app.services.ai.providers import AIProviders

# 进度回调：report(stage_name, progress)；实现方负责取消检查与单调性
ProgressReporter = Callable[[str, int], None]


class PipelineError(Exception):
    """管线可读失败：code 写入 ai_tasks.error_code，message 写入 error_message。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class TaskCancelled(Exception):
    """取消标记置位后由进度回调抛出，中断管线。"""


@dataclass
class PipelineContext:
    """管线输入。只携带非敏感元数据（对齐 ai_tasks.input_data 约束）。"""

    task_id: uuid.UUID
    record_id: uuid.UUID
    uploaded_file_id: uuid.UUID
    remarks: str | None = None
    # M4：阶段间传递的中间产物（帧路径、OCR 文本、transcript 等）
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """管线产出（M4 draft 阶段返回）。

    - ``fields``：业务记录列更新（键必须为该记录模型的真实列名）。
    - ``items`` / ``images``：子记录整体替换列表（dict 列表，键为子表列名）。
    """

    fields: dict[str, Any] = field(default_factory=dict)
    items: list[dict[str, Any]] | None = None
    images: list[dict[str, Any]] | None = None


class GenerationPipeline:
    # 关联业务实体种类（worker 据此定位记录）：inspection_record / photo_report / interview_record
    record_kind: ClassVar[str]
    # 管线依赖的 AI 能力（见 app/services/ai/providers.py）
    required_capabilities: ClassVar[tuple[str, ...]]
    # (阶段名, 进入该阶段时的进度)；阶段名写入 ai_tasks.current_stage，进度单调递增
    stages: ClassVar[tuple[tuple[str, int], ...]]

    def run(
        self,
        ctx: PipelineContext,
        providers: AIProviders,
        report: ProgressReporter,
    ) -> PipelineResult:
        missing = providers.missing(self.required_capabilities)
        if missing:
            raise PipelineError(
                "AI_SERVICE_NOT_CONFIGURED",
                "AI 服务未配置：缺少 "
                + "、".join(missing)
                + " 能力的环境变量配置，请联系管理员配置后重试",
            )
        result = PipelineResult()
        for stage, progress in self.stages:
            report(stage, progress)
            stage_result = self.execute_stage(stage, ctx, providers)
            if stage_result is not None:
                result = stage_result
        return result

    def execute_stage(
        self, stage: str, ctx: PipelineContext, providers: AIProviders
    ) -> PipelineResult | None:
        """执行单个阶段；最后一个阶段（draft）返回 PipelineResult。

        M2 默认实现不产出任何结果：AI provider 调用在 M4 接入前一律失败，
        禁止返回编造的结构化数据。M4 在子类中重写本方法。
        """
        raise PipelineError(
            "AI_PROVIDER_NOT_IMPLEMENTED",
            f"AI 处理阶段 {stage} 尚未接入真实提供商（M4 交付），任务无法继续",
        )
