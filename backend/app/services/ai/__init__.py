"""AI 能力服务（ARCHITECTURE.md §7.4）。

各能力 client 均为 OpenAI 兼容 HTTP API 实现，职责边界见 AI_CONTEXT.md
（LLM 推理 / Vision 图像理解 / OCR 文字提取 / Speech 转写 / Embedding 检索向量 /
Reranker 重排，相互独立）。模型与密钥一律来自环境变量配置，业务管线只依赖
本包接口。未配置时调用抛 AI_SERVICE_NOT_CONFIGURED，绝不编造结果。
"""

from app.services.ai.providers import AIProviders, get_ai_providers

__all__ = ["AIProviders", "get_ai_providers"]
