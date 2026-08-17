"""OpenAI 兼容 HTTP 调用基础设施：超时、有限重试、可读错误。

- 全部 provider/base_url/model/api_key 来自 ``get_settings()``，禁止硬编码。
- 失败一律抛 ``AppException``（错误信封对齐 API.md §1.3），绝不吞错。
- 测试可注入 ``transport``（httpx.MockTransport）或整体替换服务实例。
"""

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger("ai.http")


def ai_not_configured(capability: str) -> AppException:
    return AppException(
        "AI_SERVICE_NOT_CONFIGURED",
        f"AI 能力 {capability} 未配置：缺少对应的环境变量（API Key / 模型 / Base URL），"
        "请联系管理员配置后重试",
        500,
    )


def ai_service_error(message: str) -> AppException:
    return AppException("AI_SERVICE_ERROR", message, 500)


class OpenAICompatClient:
    """OpenAI 兼容 API 的最小 POST 客户端（同步 httpx，超时 + 有限重试）。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        s = settings or get_settings()
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = s.AI_HTTP_TIMEOUT_SECONDS
        self._max_retries = max(0, s.AI_HTTP_MAX_RETRIES)
        self._transport = transport

    def post_json(self, path: str, payload: dict) -> dict:
        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        last_error: str | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(
                    timeout=self._timeout, transport=self._transport
                ) as client:
                    resp = client.post(url, json=payload, headers=headers)
                if resp.status_code >= 500 or resp.status_code == 429:
                    last_error = f"HTTP {resp.status_code}"
                    logger.info("AI 请求失败（可重试）: %s attempt=%d", last_error, attempt)
                    continue
                if resp.status_code >= 400:
                    raise ai_service_error(
                        f"AI 服务拒绝请求（HTTP {resp.status_code}）：请检查模型配置与密钥"
                    )
                return resp.json()
            except httpx.TimeoutException:
                last_error = "请求超时"
                logger.info("AI 请求超时 attempt=%d", attempt)
            except httpx.TransportError as exc:
                last_error = f"网络错误（{type(exc).__name__}）"
                logger.info("AI 请求网络错误 attempt=%d: %s", attempt, type(exc).__name__)
        raise ai_service_error(f"AI 服务调用失败：{last_error}，已重试 {self._max_retries} 次")
