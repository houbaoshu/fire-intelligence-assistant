"""Interview record generation pipeline.

Audio -> speech transcription -> LLM structured extraction -> record
(per AI_CONTEXT.md / specs/interview-record.md).
"""
from __future__ import annotations

import uuid

from app.core.exceptions import AIProviderError
from app.models.interview import InterviewRecord
from app.prompts.interview import INTERVIEW_EXTRACTION_PROMPT, INTERVIEW_SYSTEM
from app.services.ai.llm import LLMService
from app.services.ai.speech import SpeechService
from app.services.file_service import FileService
from app.services.tasks.registry import TaskContext, register_handler


@register_handler("interview_record_generation")
def handle_interview_generation(ctx: TaskContext) -> None:
    record_id = uuid.UUID(ctx.input_data["record_id"])
    file_id = uuid.UUID(ctx.input_data["uploaded_file_id"])

    file_service = FileService(ctx.db)
    uploaded = file_service.get_record(file_id)
    audio_bytes = file_service.storage.open_bytes(uploaded.storage_path)

    # 1. speech transcription
    ctx.set_progress(20, "speech_transcription")
    speech = SpeechService()
    transcript = speech.transcribe(audio_bytes, uploaded.original_name or "audio.mp3")
    if not transcript.strip():
        raise AIProviderError("未识别到可辨识的语音内容")

    # 2. LLM structured extraction
    ctx.set_progress(70, "llm_extraction")
    llm = LLMService()
    structured = llm.structured(
        INTERVIEW_SYSTEM,
        INTERVIEW_EXTRACTION_PROMPT.format(transcript=transcript),
    )

    # 3. persist (transcript and structured content kept separate)
    ctx.set_progress(90, "saving")
    record = ctx.db.get(InterviewRecord, record_id)
    if record is None:
        raise AIProviderError("询问记录草稿不存在")
    record.transcript = transcript
    record.structured_content = structured
    record.title = (structured.get("title") or "").strip() or record.title
    record.interviewee_name = (structured.get("interviewee_name") or "").strip()
    record.interviewer_names = structured.get("interviewer_names") or []
    record.location = (structured.get("location") or "").strip()
    record.started_at = _parse_dt(structured.get("started_at"))
    record.ended_at = _parse_dt(structured.get("ended_at"))
    record.status = "generated"
    ctx.db.flush()
    ctx.set_result({"record_id": str(record_id)})


def _parse_dt(value):
    from datetime import datetime

    if not value:
        return None
    try:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except ValueError:
        return None
