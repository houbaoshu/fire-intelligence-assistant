"""AI 能力服务抽象（ARCHITECTURE.md §7.4）。

M2 仅提供配置探测：各能力是否已在环境变量中配置。M4 在本包中补充
LLMService / VisionService / OCRService / SpeechService 的真实实现
（OpenAI 兼容 API），业务管线只依赖本包接口，不出现具体模型名与密钥。
"""

from app.services.ai.providers import AIProviders, get_ai_providers

__all__ = ["AIProviders", "get_ai_providers"]
