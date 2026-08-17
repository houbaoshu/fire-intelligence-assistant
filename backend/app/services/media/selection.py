"""关键帧筛选：模糊质量过滤 + 感知哈希去重（numpy/Pillow 实现）。

机械筛选只做初筛（specs/photo-report.md：模糊/过暗/重复帧自动排除，
审阅阶段用户可再排除）；不做任何内容理解。
"""

import io

import numpy as np
from PIL import Image

from app.core.logging import get_logger
from app.services.media.video import VideoFrame

logger = get_logger("media.selection")

# 拉普拉斯方差低于该值视为模糊/纯色帧（64x64 灰度图）
BLUR_VARIANCE_THRESHOLD = 10.0
# 8x8 感知哈希汉明距离小于该值视为重复帧
DEDUP_HAMMING_THRESHOLD = 6


def _gray_array(data: bytes, size: int = 64) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as img:
        resized = img.convert("L").resize((size, size))
        return np.asarray(resized, dtype=np.float64)


def blur_score(data: bytes) -> float:
    """拉普拉斯方差：值越低画面越模糊（纯色帧接近 0）。"""
    gray = _gray_array(data)
    lap = (
        -4 * gray[1:-1, 1:-1]
        + gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
    )
    return float(lap.var())


def ahash(data: bytes) -> int:
    """8x8 平均感知哈希（64 bit int）。"""
    gray = _gray_array(data, size=8)
    bits = gray > gray.mean()
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return value


def select_key_frames(
    frames: list[VideoFrame],
    *,
    max_frames: int,
    blur_threshold: float = BLUR_VARIANCE_THRESHOLD,
    hamming_threshold: int = DEDUP_HAMMING_THRESHOLD,
) -> tuple[list[VideoFrame], list[tuple[VideoFrame, str]]]:
    """模糊过滤 + 去重，返回 (保留帧, [(丢弃帧, 原因)])。保留时间顺序。

    任何单帧解析失败不中断流程：该帧按「无法解析」丢弃并记录原因。
    """
    kept: list[VideoFrame] = []
    dropped: list[tuple[VideoFrame, str]] = []
    kept_hashes: list[int] = []
    for frame in frames:
        try:
            score = blur_score(frame.data)
            digest = ahash(frame.data)
        except Exception:  # Pillow 无法解码的帧一律丢弃并留痕
            logger.info("关键帧筛选：%.3fs 帧无法解析，丢弃", frame.timestamp)
            dropped.append((frame, "帧图像无法解析"))
            continue
        if score < blur_threshold:
            dropped.append((frame, "画面模糊或无有效内容"))
            continue
        if any(
            (digest ^ existing).bit_count() < hamming_threshold
            for existing in kept_hashes
        ):
            dropped.append((frame, "与已保留帧重复"))
            continue
        kept.append(frame)
        kept_hashes.append(digest)
    if len(kept) > max_frames:
        # 超限时按时间均匀抽样，保留首尾覆盖
        indices = np.linspace(0, len(kept) - 1, max_frames).round().astype(int)
        selected = sorted(set(int(i) for i in indices))
        overflow = [frame for i, frame in enumerate(kept) if i not in selected]
        dropped.extend((frame, "超过关键帧数量上限") for frame in overflow)
        kept = [kept[i] for i in selected]
    return kept, dropped
