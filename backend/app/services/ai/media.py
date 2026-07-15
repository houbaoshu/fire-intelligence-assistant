from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageStat

from app.core.exceptions import AppError


def _ffmpeg() -> str:
    executable = shutil.which("ffmpeg")
    if not executable:
        raise AppError(
            status_code=503,
            code="MEDIA_PROCESSOR_UNAVAILABLE",
            message="FFmpeg is required for media processing but is not installed.",
        )
    return executable


def extract_frames(video_path: Path, output_dir: Path, maximum: int) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame-%03d.jpg"
    command = [
        _ffmpeg(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        "fps=1/8,scale='min(1280,iw)':-2",
        "-frames:v",
        str(maximum),
        "-q:v",
        "3",
        str(pattern),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
    frames = sorted(output_dir.glob("frame-*.jpg"))
    if result.returncode != 0 or not frames:
        raise AppError(
            status_code=422,
            code="FRAME_EXTRACTION_FAILED",
            message="No usable frames could be extracted from the video.",
        )
    return frames


def filter_evidence_frames(frames: list[Path]) -> list[Path]:
    """Reject flat/dark frames and near-duplicates using a small perceptual hash."""
    selected: list[Path] = []
    hashes: list[int] = []
    for frame in frames:
        try:
            with Image.open(frame) as image:
                grayscale = image.convert("L")
                statistics = ImageStat.Stat(grayscale)
                mean = statistics.mean[0]
                variance = statistics.var[0]
                if mean < 15 or mean > 245 or variance < 12:
                    continue
                resized = grayscale.resize((8, 8))
                pixels = list(resized.getdata())
                average = sum(pixels) / len(pixels)
                fingerprint = sum(
                    1 << index for index, value in enumerate(pixels) if value >= average
                )
        except OSError:
            continue
        if any((fingerprint ^ existing).bit_count() <= 5 for existing in hashes):
            continue
        hashes.append(fingerprint)
        selected.append(frame)
    return selected


def extract_audio(media_path: Path, output_path: Path) -> Path:
    command = [
        _ffmpeg(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(media_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        "-y",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
    if result.returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
        raise AppError(
            status_code=422,
            code="AUDIO_EXTRACTION_FAILED",
            message="No usable audio could be extracted from the recording.",
        )
    return output_path
