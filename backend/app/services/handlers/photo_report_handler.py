"""Photo report generation pipeline.

Video -> key frame extraction -> dedup -> vision analysis -> captions ->
structured report (per AI_CONTEXT.md / specs/photo-report.md).
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import AIProviderError
from app.models.photo_report import PhotoReport, PhotoReportImage
from app.prompts.photo_report import (
    PHOTO_CAPTION_SYSTEM,
    PHOTO_REPORT_SUMMARY_PROMPT,
    PHOTO_REPORT_SUMMARY_SYSTEM,
)
from app.services.ai.llm import LLMService
from app.services.ai.vision import VisionService
from app.services.media_service import extract_frames
from app.services.tasks.registry import TaskContext, register_handler
from app.services.file_service import FileService

FRAME_INTERVAL = 3.0
MAX_CANDIDATES = 30


@register_handler("photo_report_generation")
def handle_photo_report_generation(ctx: TaskContext) -> None:
    from app.core.exceptions import ValidationError

    report_id = uuid.UUID(ctx.input_data["report_id"])
    file_id = uuid.UUID(ctx.input_data["uploaded_file_id"])

    settings = get_settings()
    workdir = Path(settings.temporary_dir) / str(ctx.task_id)
    frames_dir = workdir / "frames"
    workdir.mkdir(parents=True, exist_ok=True)

    try:
        file_service = FileService(ctx.db)
        uploaded = file_service.get_record(file_id)
        video_bytes = file_service.storage.open_bytes(uploaded.storage_path)
        video_path = workdir / "source.mp4"
        video_path.write_bytes(video_bytes)

        ctx.set_progress(15, "frame_extraction")
        frames = extract_frames(video_path, frames_dir, interval_seconds=FRAME_INTERVAL)
        frames = frames[:MAX_CANDIDATES]

        vision = VisionService()
        llm = LLMService()
        analyzed: list[dict] = []

        total = len(frames)
        for i, frame in enumerate(frames):
            ctx.set_progress(15 + int(55 * (i / max(total, 1))), "vision_analysis")
            image_bytes = frame["path"].read_bytes()
            try:
                caption_json = vision.analyze_image(
                    PHOTO_CAPTION_SYSTEM
                    + "\n\n请分析这张消防检查现场照片并输出要求的 JSON。",
                    image_bytes,
                )
            except AIProviderError:
                continue
            parsed = _parse_caption_json(caption_json)
            if not parsed or not parsed.get("caption"):
                continue
            analyzed.append(
                {
                    "path": frame["path"],
                    "timestamp": frame["timestamp"],
                    "caption": parsed["caption"],
                    "address": parsed.get("detected_address", ""),
                    "violation": parsed.get("detected_violation", ""),
                }
            )

        if not analyzed:
            ctx.set_progress(80, "llm_extraction")
            report = ctx.db.get(PhotoReport, report_id)
            if report:
                report.status = "generated"
                report.violation_summary = "未识别到可用照片,请人工补充检查照片。"
            ctx.set_result({"record_id": str(report_id)})
            return

        # dedupe by caption similarity (simple exact/near-duplicate heuristic)
        deduped = _dedupe(analyzed)

        # store extracted frames as uploaded files (permanent key-frames)
        ctx.set_progress(80, "saving_frames")
        images_out: list[dict] = []
        for item in deduped:
            data = item["path"].read_bytes()
            uploaded_file = file_service.store_bytes(
                data, "image", f"frame_{item['timestamp']:.2f}.jpg", ctx.user_id, mime="image/jpeg"
            )
            images_out.append(
                {
                    "uploaded_file_id": uploaded_file.id,
                    "frame_timestamp": item["timestamp"],
                    "caption": item["caption"],
                    "detected_address": item["address"],
                    "detected_violation": item["violation"],
                }
            )

        ctx.set_progress(90, "llm_extraction")
        report = ctx.db.get(PhotoReport, report_id)
        if report is None:
            raise AIProviderError("拍照报告草稿不存在")
        for order, img in enumerate(images_out):
            ctx.db.add(
                PhotoReportImage(
                    photo_report_id=report.id,
                    uploaded_file_id=img["uploaded_file_id"],
                    frame_timestamp=img["frame_timestamp"],
                    caption=img["caption"],
                    detected_address=img["detected_address"],
                    detected_violation=img["detected_violation"],
                    is_selected=True,
                    sort_order=order,
                )
            )
        # report-level fields from LLM summary
        items_text = "\n".join(
            f"- 时间点{i['frame_timestamp']}s: {i['caption']}" for i in images_out
        )
        try:
            summary = llm.structured(
                PHOTO_REPORT_SUMMARY_SYSTEM,
                PHOTO_REPORT_SUMMARY_PROMPT.format(items=items_text),
            )
            report.title = (summary.get("title") or "").strip() or report.title
            report.inspection_unit = (summary.get("inspection_unit") or "").strip()
            report.inspection_address = (summary.get("inspection_address") or "").strip()
            report.violation_summary = (summary.get("violation_summary") or "").strip()
        except AIProviderError:
            report.violation_summary = items_text[:2000]
        report.status = "generated"
        ctx.db.flush()
        ctx.set_result({"record_id": str(report_id)})
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _parse_caption_json(text: str) -> dict | None:
    import json

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


def _dedupe(items: list[dict]) -> list[dict]:
    """Remove near-duplicate frames (same timestamp bucket or identical caption)."""
    result: list[dict] = []
    seen_captions: set[str] = set()
    for item in items:
        key = item["caption"].strip()[:50]
        if key and key in seen_captions:
            continue
        if key:
            seen_captions.add(key)
        result.append(item)
    return result
