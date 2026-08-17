"""媒体处理临时工作区。

中间产物（写盘的视频副本、抽帧输出、音频轨）放在
``<MEDIA_TEMP_DIR>/<task_id>/``（默认 data/temporary/，见 ARCHITECTURE.md
§7.6），退出上下文时无条件清理（specs/_common.md：临时文件与中间产物
必须在使用后清理）。
"""

import shutil
import uuid
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger("media.workspace")


class MediaWorkspace:
    def __init__(
        self, task_id: uuid.UUID, settings: Settings | None = None
    ) -> None:
        settings = settings or get_settings()
        self.dir = Path(settings.MEDIA_TEMP_DIR).resolve() / task_id.hex

    def __enter__(self) -> "MediaWorkspace":
        self.dir.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, *_exc) -> None:
        try:
            shutil.rmtree(self.dir, ignore_errors=True)
        except OSError:
            logger.warning("临时工作区清理失败: %s", self.dir, exc_info=True)

    def path(self, name: str) -> Path:
        """工作区内的一个文件路径（name 为纯文件名，防路径穿越）。"""
        safe = Path(name).name
        return self.dir / safe
