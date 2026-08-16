"""Inspection record generation pipeline.

Video -> frame extraction -> vision analysis -> OCR -> speech transcription
-> LLM structured extraction -> structured record (per AI_CONTEXT.md).
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import AIProviderError, DocumentGenerationError
from app.models.inspection import InspectionRecord, InspectionRecordItem
from app.prompts.inspection import (
    INSPECTION_EXTRACTION_PROMPT,
    INSPECTION_SUMMARY_PROMPT,
    INSPECTION_SYSTEM,
)
from app.services.ai.llm import LLMService
from app.services.ai.ocr import OCRService
from app.services.ai.speech import SpeechService
from app.services.ai.vision import VisionService
from app.services.media_service import extract_audio, extract_frames
from app.services.tasks.registry import TaskContext, register_handler

FRAME_INTERVAL = 8.0
MAX_FRAMES_FOR_ANALYSIS = 12


@register_handler("inspection_record_generation")
def handle_inspection_generation(ctx: TaskContext) -> None:
    from app.services.file_service import FileService

    record_id = uuid.UUID(ctx.input_data["record_id"])
    file_id = uuid.UUID(ctx.input_data["uploaded_file_id"])
    remarks = ctx.input_data.get("remarks", "")

    settings = get_settings()
    workdir = Path(settings.temporary_dir) / str(ctx.task_id)
    frames_dir = workdir / "frames"
    audio_path = workdir / "audio.wav"
    workdir.mkdir(parents=True, exist_ok=True)

    try:
        file_service = FileService(ctx.db)
        video_bytes = file_service.storage.open_bytes(
            file_service.get_record(file_id).storage_path
        )
        video_path = workdir / "source_video.mp4"
        video_path.write_bytes(video_bytes)

        # 1. frame extraction
        ctx.set_progress(10, "frame_extraction")
        frames = extract_frames(video_path, frames_dir, interval_seconds=FRAME_INTERVAL)

        # 2. vision + OCR analysis on a sample of frames
        vision = VisionService()
        ocr = OCRService()
        frame_analyses: list[str] = []
        ocr_parts: list[str] = []
        sample = frames[:MAX_FRAMES_FOR_ANALYSIS]
        total = len(sample)
        for i, frame in enumerate(sample):
            ctx.set_progress(
                10 + int(30 * (i / max(total, 1))),
                "vision_analysis" if i == 0 else None,
            )
            image_bytes = frame["path"].read_bytes()
            try:
                analysis = vision.analyze_image(
                    "请描述这张消防检查现场照片:画面中可见的场所、设备、人员活动、可能存在的消防安全隐患。"
                    "只描述画面中明确可见的内容,不确定的不要猜测。",
                    image_bytes,
                )
                frame_analyses.append(f"时间点{frame['timestamp']}s:{analysis}")
            except AIProviderError:
                ctx.set_progress(10 + int(30 * (i / max(total, 1))), "vision_analysis")
                continue
            try:
                ocr_text = ocr.extract_text(image_bytes)
                if ocr_text.strip():
                    ocr_parts.append(f"时间点{frame['timestamp']}s:{ocr_text.strip()}")
            except AIProviderError:
                continue

        # 3. audio -> speech transcription
        ctx.set_progress(55, "speech_transcription")
        transcript = ""
        try:
            extract_audio(video_path, audio_path)
            speech = SpeechService()
            transcript = speech.transcribe(audio_path.read_bytes(), "audio.wav")
        except (AIProviderError, DocumentGenerationError):
            transcript = ""

        # 4. LLM structured extraction
        ctx.set_progress(75, "llm_extraction")
        llm = LLMService()
        vision_summary = ""
        if frame_analyses:
            vision_summary = llm.chat(
                "你是消防检查分析助手。将以下帧分析整合为简洁摘要。",
                INSPECTION_SUMMARY_PROMPT.format(frames="\n".join(frame_analyses)),
                temperature=0.1,
            )
        structured = llm.structured(
            INSPECTION_SYSTEM,
            INSPECTION_EXTRACTION_PROMPT.format(
                remarks=remarks or "(无)",
                vision_summary=vision_summary or "(无画面分析结果)",
                ocr_text="\n".join(ocr_parts) or "(无OCR结果)",
                transcript=transcript or "(无语音转写结果)",
            ),
        )

        # 5. persist structured record
        ctx.set_progress(90, "saving")
        record = ctx.db.get(InspectionRecord, record_id)
        if record is None:
            raise AIProviderError("检查记录草稿不存在")
        _apply_structured(record, structured, ctx.db)
        record.status = "generated"
        ctx.db.flush()
        ctx.set_result({"record_id": str(record_id)})
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _apply_structured(record: InspectionRecord, data: dict, db) -> None:
    record.title = _clean(data.get("title")) or record.title
    record.inspection_unit = _clean(data.get("inspection_unit"))
    record.inspection_address = _clean(data.get("inspection_address"))
    record.inspector_names = data.get("inspector_names") or []
    record.contact_person = _clean(data.get("contact_person"))
    record.contact_phone = _clean(data.get("contact_phone"))
    record.summary = _clean(data.get("summary"))
    record.conclusion = _clean(data.get("conclusion"))
    # inspection_date: keep as None unless clearly parseable
    date_raw = data.get("inspection_date")
    if date_raw:
        try:
            from datetime import date, datetime

            if isinstance(date_raw, str):
                record.inspection_date = date.fromisoformat(date_raw[:10])
            else:
                record.inspection_date = datetime.fromisoformat(str(date_raw))
        except ValueError:
            record.inspection_date = None
    else:
        record.inspection_date = None

    items = data.get("items") or []
    for old in record.items:
        db.delete(old)
    for order, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("description"):
            continue
        db.add(
            InspectionRecordItem(
                inspection_record_id=record.id,
                item_type=item.get("item_type", "observation") or "observation",
                location=_clean(item.get("location")),
                description=str(item.get("description", "")),
                legal_basis=_clean(item.get("legal_basis")),
                correction_requirement=_clean(item.get("correction_requirement")),
                severity=_clean(item.get("severity")),
                sort_order=order,
            )
        )


def _clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
