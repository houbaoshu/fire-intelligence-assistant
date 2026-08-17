"""视频/音频媒体处理（M4 文书生成管线）。

职责边界（AI_CONTEXT.md Video Workflow / ARCHITECTURE.md §11-13）：
ffmpeg 进程只做机械处理（抽帧、抽音频），图像质量筛选用 numpy/Pillow
实现；内容理解归 Vision/OCR/Speech 能力服务。临时中间产物一律放在
``temporary/`` 工作区，用后清理（specs/_common.md）。
"""

from app.services.media.selection import select_key_frames
from app.services.media.video import (
    MediaProcessingError,
    VideoFrame,
    extract_audio,
    extract_frames,
    has_audio_stream,
)
from app.services.media.workspace import MediaWorkspace

__all__ = [
    "MediaProcessingError",
    "MediaWorkspace",
    "VideoFrame",
    "extract_audio",
    "extract_frames",
    "has_audio_stream",
    "select_key_frames",
]
