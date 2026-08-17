"""媒体处理测试：抽帧、音频抽取、去重/质量筛选、临时工作区清理。

测试视频由 imageio-ffmpeg 自带的 ffmpeg 合成（外部进程边界内自洽），
不依赖系统 ffmpeg 或网络。
"""

import io
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import pytest
from PIL import Image

from app.services.media import (
    MediaWorkspace,
    extract_audio,
    extract_frames,
    has_audio_stream,
    select_key_frames,
)
from app.services.media.video import MediaProcessingError, VideoFrame


@pytest.fixture(scope="module")
def video_with_audio(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("media")
    video = tmp / "scene.mp4"
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [exe, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=duration=5:size=64x64:rate=10",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
         "-shortest", str(video)],
        capture_output=True,
    )
    assert proc.returncode == 0
    return video


@pytest.fixture(scope="module")
def video_no_audio(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("media-noaudio")
    video = tmp / "silent.mp4"
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [exe, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=duration=2:size=64x64:rate=5", str(video)],
        capture_output=True,
    )
    assert proc.returncode == 0
    return video


def test_extract_frames_count_and_timestamps(video_with_audio, tmp_path):
    frames = extract_frames(
        video_with_audio, tmp_path / "frames", interval_seconds=2.0, max_frames=10
    )
    # 5 秒视频按 2s 间隔：约 3 帧
    assert len(frames) == 3
    timestamps = [f.timestamp for f in frames]
    assert timestamps == sorted(timestamps)
    assert timestamps[0] < 1.0  # 首帧接近 0s
    assert abs(timestamps[-1] - 4.0) < 1.0
    for frame in frames:
        assert frame.data[:2] == b"\xff\xd8"  # JPEG 签名


def test_extract_frames_max_frames_cap(video_with_audio, tmp_path):
    frames = extract_frames(
        video_with_audio, tmp_path / "frames", interval_seconds=0.5, max_frames=2
    )
    assert len(frames) == 2


def test_extract_frames_invalid_video(tmp_path):
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64)
    with pytest.raises(MediaProcessingError) as exc_info:
        extract_frames(bad, tmp_path / "frames", interval_seconds=1.0, max_frames=5)
    assert "抽帧" in str(exc_info.value) or "解析" in str(exc_info.value)


def test_extract_audio(video_with_audio, video_no_audio, tmp_path):
    out = tmp_path / "a.wav"
    assert extract_audio(video_with_audio, out) is True
    assert out.read_bytes()[:4] == b"RIFF"
    # 无音频轨：返回 False 而不是报错
    assert has_audio_stream(video_no_audio) is False
    assert extract_audio(video_no_audio, tmp_path / "b.wav") is False


def _jpeg(array: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(array).save(buf, format="JPEG")
    return buf.getvalue()


def _noise_frame(timestamp: float, seed: int) -> VideoFrame:
    rng = np.random.default_rng(seed)
    return VideoFrame(timestamp=timestamp, data=_jpeg(rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)))


def test_select_key_frames_dedup_and_blur():
    blurry = VideoFrame(timestamp=0.0, data=_jpeg(np.full((64, 64, 3), 128, dtype=np.uint8)))
    a1 = _noise_frame(1.0, seed=1)
    a1_dup = VideoFrame(timestamp=2.0, data=a1.data)  # 完全相同 → 重复
    b = _noise_frame(3.0, seed=2)
    kept, dropped = select_key_frames([blurry, a1, a1_dup, b], max_frames=10)
    assert [f.timestamp for f in kept] == [1.0, 3.0]
    reasons = [reason for _, reason in dropped]
    assert any("模糊" in r for r in reasons)
    assert any("重复" in r for r in reasons)


def test_select_key_frames_max_cap_even_sampling():
    frames = [_noise_frame(float(i), seed=100 + i) for i in range(10)]
    kept, dropped = select_key_frames(frames, max_frames=4)
    assert len(kept) == 4
    assert len(dropped) == 6
    # 均匀抽样：首尾覆盖
    assert kept[0].timestamp == 0.0
    assert kept[-1].timestamp == 9.0


def test_media_workspace_cleanup():
    import uuid

    with MediaWorkspace(uuid.uuid4()) as workspace:
        path = workspace.path("x.bin")
        path.write_bytes(b"data")
        assert path.exists()
        workspace_dir = workspace.dir
    assert not workspace_dir.exists()
