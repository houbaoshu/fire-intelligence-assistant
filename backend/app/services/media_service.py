"""Media processing: video frame extraction and audio extraction via ffmpeg.

Frames and audio are temporary intermediates; callers must clean them up.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

logger = get_logger("media")


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise AIProviderError("服务器缺少 ffmpeg,无法处理音视频")
    return path


def extract_frames(video_path: Path, out_dir: Path, interval_seconds: float = 5.0) -> list[dict]:
    """Extract one frame per interval. Returns [{path, timestamp}]."""
    ffmpeg = _require_ffmpeg()
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / "frame"
    cmd = [
        ffmpeg, "-y", "-i", str(video_path),
        "-vf", f"fps=1/{interval_seconds}",
        "-q:v", "2",
        str(prefix) + "_%06d.jpg",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        logger.warning("frame extraction failed: %s", proc.stderr[-500:])
        raise AIProviderError("视频抽帧失败")
    frames = sorted(out_dir.glob("frame_*.jpg"))
    if not frames:
        # very short video: extract at least one frame from the start
        first = out_dir / "frame_000001.jpg"
        cmd2 = [
            ffmpeg, "-y", "-i", str(video_path),
            "-frames:v", "1", "-q:v", "2", str(first),
        ]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
        if proc2.returncode == 0 and first.exists():
            frames = [first]
    result = []
    for i, f in enumerate(frames):
        result.append({"path": f, "timestamp": round(i * interval_seconds, 2)})
    return result


def extract_audio(video_path: Path, out_path: Path) -> Path:
    """Extract audio track as wav."""
    ffmpeg = _require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(out_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        logger.warning("audio extraction failed: %s", proc.stderr[-500:])
        raise AIProviderError("音频提取失败")
    return out_path


def probe_duration(media_path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    cmd = [
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(media_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode == 0:
            return float(proc.stdout.strip())
    except Exception:  # pragma: no cover
        pass
    return None
