"""ffmpeg 进程封装：视频抽帧与音频轨抽取。

ffmpeg 二进制由 imageio-ffmpeg 提供（自带静态编译版本，无需系统安装）。
所有外部进程失败转为 ``MediaProcessingError``（可读信息），绝不吞错。
"""

import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg

from app.core.logging import get_logger

logger = get_logger("media.video")

# showinfo 输出的帧时间戳，如 "pts_time:1.5"
_PTS_TIME_RE = re.compile(r"pts_time:([0-9.]+)")
# 探测输出中的音频流，如 "Stream #0:1: Audio: aac"
_AUDIO_STREAM_RE = re.compile(r"Stream .*Audio:")

_FFPROBE_TIMEOUT = 300  # 单个 ffmpeg 进程的最长运行时间（秒）


class MediaProcessingError(Exception):
    """媒体处理可读失败（由管线转为 PipelineError 落库）。"""


@dataclass
class VideoFrame:
    """抽取的视频帧：源视频时间戳（秒）+ JPEG 字节。"""

    timestamp: float
    data: bytes


def _run_ffmpeg(args: list[str], *, action: str) -> subprocess.CompletedProcess:
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        return subprocess.run(
            [exe, "-hide_banner", *args],
            capture_output=True,
            timeout=_FFPROBE_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise MediaProcessingError(f"{action}超时，请检查视频文件后重试")
    except OSError as exc:
        raise MediaProcessingError(f"无法启动媒体处理组件：{type(exc).__name__}")


def _stderr_text(proc: subprocess.CompletedProcess) -> str:
    return proc.stderr.decode("utf-8", errors="replace")


def has_audio_stream(video_path: Path) -> bool:
    """探测视频是否含音频轨（ffmpeg -i 的流信息输出在 stderr）。"""
    proc = _run_ffmpeg(["-i", str(video_path)], action="视频信息探测")
    return bool(_AUDIO_STREAM_RE.search(_stderr_text(proc)))


def extract_frames(
    video_path: Path,
    out_dir: Path,
    *,
    interval_seconds: float,
    max_frames: int,
) -> list[VideoFrame]:
    """按固定间隔抽取 JPEG 帧，返回 (时间戳, 字节) 列表（按时间升序）。

    时间戳来自 ffmpeg showinfo 滤镜的 pts_time，与输出帧一一对应。
    """
    if interval_seconds <= 0:
        raise ValueError("抽帧间隔必须为正数")
    if max_frames <= 0:
        raise ValueError("抽帧数量上限必须为正数")
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / f"frame-{uuid.uuid4().hex}-%06d.jpg"
    proc = _run_ffmpeg(
        [
            "-i",
            str(video_path),
            "-vf",
            f"fps=1/{interval_seconds},showinfo",
            "-frames:v",
            str(max_frames),
            "-q:v",
            "3",
            str(pattern),
        ],
        action="视频抽帧",
    )
    if proc.returncode != 0:
        tail = _stderr_text(proc).strip().splitlines()[-1:]
        logger.info("视频抽帧失败: %s", tail)
        raise MediaProcessingError("视频无法解析或抽帧失败，请确认视频文件完整可读")
    timestamps = [float(m.group(1)) for m in _PTS_TIME_RE.finditer(_stderr_text(proc))]
    paths = sorted(out_dir.glob(f"{pattern.name[:-9]}*.jpg"))
    frames = []
    for index, path in enumerate(paths):
        # fps 滤镜在不足一帧间隔时可能不产出；时间戳数量与帧数应一致
        timestamp = timestamps[index] if index < len(timestamps) else index * interval_seconds
        frames.append(VideoFrame(timestamp=round(timestamp, 3), data=path.read_bytes()))
    return frames


def extract_audio(video_path: Path, out_path: Path) -> bool:
    """抽取音频轨为 16kHz 单声道 WAV（供语音转写）。无音频轨返回 False。"""
    if not has_audio_stream(video_path):
        return False
    proc = _run_ffmpeg(
        [
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(out_path),
        ],
        action="音频抽取",
    )
    if proc.returncode != 0 or not out_path.exists():
        tail = _stderr_text(proc).strip().splitlines()[-1:]
        logger.info("音频抽取失败: %s", tail)
        raise MediaProcessingError("视频音频轨抽取失败，请确认视频文件完整可读")
    return True
