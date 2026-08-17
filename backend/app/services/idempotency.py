"""幂等提交（API.md §1.5）：Idempotency-Key 请求头的统一处理。

同一用户 + 同一端点（task_type）+ 同一 key 的重复提交返回首个任务，
不再创建重复任务/业务记录；同 key 不同请求体（摘要不一致）返回
409 IDEMPOTENCY_CONFLICT。存储在 ai_tasks（created_by, task_type,
idempotency_key 唯一索引 + request_hash 摘要，见 DATABASE.md）。
"""

import hashlib
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import AppException, conflict
from app.models.ai_task import AITask
from app.repositories.task_repository import TaskRepository

MAX_KEY_LENGTH = 200


def compute_request_hash(*parts: bytes | str | None) -> str:
    """请求体摘要：文件字节 + 表单参数，用于同 key 不同体的冲突检测。"""
    digest = hashlib.sha256()
    for part in parts:
        if part is None:
            continue
        digest.update(part.encode() if isinstance(part, str) else part)
        digest.update(b"\x00")
    return digest.hexdigest()


def find_idempotent_task(
    session: Session,
    *,
    user_id: uuid.UUID,
    task_type: str,
    idempotency_key: str | None,
    request_hash: str,
) -> AITask | None:
    """返回可复用的首个任务；key 冲突（同 key 不同体）抛 409。未带 key 返回 None。"""
    if idempotency_key is None:
        return None
    if not idempotency_key or len(idempotency_key) > MAX_KEY_LENGTH:
        raise AppException(
            "VALIDATION_ERROR",
            f"Idempotency-Key 长度须在 1-{MAX_KEY_LENGTH} 字符之间",
            400,
        )
    existing = TaskRepository(session).find_by_idempotency(
        user_id, task_type, idempotency_key
    )
    if existing is None:
        return None
    if existing.request_hash != request_hash:
        raise conflict(
            "IDEMPOTENCY_CONFLICT",
            "相同 Idempotency-Key 携带了不同的请求内容，请更换 key 后重试",
        )
    return existing
