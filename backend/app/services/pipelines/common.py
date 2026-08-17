"""三条生成管线的共享辅助。

- 源文件读取（uploaded_files + 对象存储）；
- 关键帧落对象存储 ``key-frames/`` 并登记 uploaded_files（category=image），
  供 photo_report_images 引用；
- LLM 结构化输出解析（解析失败按任务失败处理，不得把原始文本当结果）；
- 检查记录编号生成（JC-年份-序号，见 docs/DATABASE.md record_number 约束）。

管线在 worker 线程中运行，与请求会话隔离：这里统一使用独立 DB 会话。
"""

import hashlib
import json
import re
import uuid
from datetime import datetime

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db import SessionLocal
from app.models.inspection import InspectionRecord
from app.models.uploaded_file import UploadedFile
from app.services.media.video import MediaProcessingError
from app.services.pipelines.base import PipelineContext, PipelineError
from app.services.storage import StorageService, get_storage_service

logger = get_logger("pipelines.common")

# LLM 输出常见包裹：```json ... ```
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def load_source_bytes(
    ctx: PipelineContext, storage: StorageService
) -> tuple[UploadedFile, bytes]:
    """读取任务源文件的元数据与字节；缺失时抛出可读管线错误。"""
    session = SessionLocal()
    try:
        file = session.get(UploadedFile, ctx.uploaded_file_id)
        if file is None or file.deleted_at is not None:
            raise PipelineError(
                "SOURCE_FILE_NOT_FOUND", "任务关联的源文件不存在或已删除，无法继续生成"
            )
        try:
            data = storage.read(file.storage_path)
        except (OSError, ValueError):
            raise PipelineError(
                "SOURCE_FILE_UNREADABLE", "源文件读取失败，请重新上传后重试"
            )
        return file, data
    finally:
        session.close()


def register_key_frame(
    *, frame_data: bytes, uploaded_by: uuid.UUID, storage: StorageService
) -> uuid.UUID:
    """把关键帧写入对象存储 key-frames/ 并登记 uploaded_files（category=image）。

    独立事务立即提交：photo_report_images 需要可引用的已存在文件 ID。
    """
    storage_key = f"key-frames/{uuid.uuid4().hex}.jpg"
    storage.save(storage_key, frame_data)
    session = SessionLocal()
    try:
        file = UploadedFile(
            original_name=f"key-frame-{uuid.uuid4().hex[:8]}.jpg",
            storage_path=storage_key,
            storage_provider=get_settings().STORAGE_PROVIDER,
            mime_type="image/jpeg",
            file_extension=".jpg",
            size_bytes=len(frame_data),
            checksum=hashlib.sha256(frame_data).hexdigest(),
            category="image",
            uploaded_by=uploaded_by,
        )
        session.add(file)
        session.commit()
        return file.id
    except Exception:
        session.rollback()
        storage.delete(storage_key)  # 登记失败时清理存储对象，避免孤儿文件
        raise
    finally:
        session.close()


def parse_llm_json(text: str, *, stage: str) -> dict:
    """解析 LLM 结构化输出为 JSON 对象；失败按任务失败处理（不吞错、不降级为原文）。"""
    cleaned = _CODE_FENCE_RE.sub("", text.strip())
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.info("LLM 输出非 JSON（阶段 %s）：%.200s", stage, text)
        raise PipelineError(
            "AI_OUTPUT_INVALID",
            f"AI 在 {stage} 阶段返回了无法解析的内容，任务失败，请重试",
        )
    if not isinstance(value, dict):
        raise PipelineError(
            "AI_OUTPUT_INVALID",
            f"AI 在 {stage} 阶段返回的内容不是结构化 JSON 对象，任务失败，请重试",
        )
    return value


def parse_datetime(value: object) -> datetime | None:
    """宽松解析 LLM 产出的日期/时间字符串；无法解析返回 None（留空，不编造）。"""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=None)
        except ValueError:
            continue
    return None


def next_record_number(prefix: str = "JC") -> str:
    """生成检查记录编号：JC-<年份>-<四位序号>（序号按当年已有编号数递增）。

    record_number 有唯一约束：并发生成冲突时任务以可读错误失败，可重试。
    """
    year = datetime.now().year
    like = f"{prefix}-{year}-%"
    session = SessionLocal()
    try:
        count = session.scalar(
            select(func.count())
            .select_from(InspectionRecord)
            .where(InspectionRecord.record_number.like(like))
        )
        return f"{prefix}-{year}-{(count or 0) + 1:04d}"
    finally:
        session.close()


def media_failed(exc: MediaProcessingError, stage: str) -> PipelineError:
    return PipelineError("MEDIA_PROCESSING_FAILED", f"{stage}：{exc}")


def warn(ctx: PipelineContext, message: str) -> None:
    """记录部分失败的降级说明：进日志与 ctx.artifacts['warnings']（不静默）。"""
    logger.info("管线降级（任务 %s）：%s", ctx.task_id, message)
    ctx.artifacts.setdefault("warnings", []).append(message)
