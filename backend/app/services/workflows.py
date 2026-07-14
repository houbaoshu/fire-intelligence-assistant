from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from sqlalchemy import delete, select

from app.core.exceptions import AppError
from app.db.models import (
    InspectionRecord,
    InspectionRecordItem,
    InterviewRecord,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeIndexJob,
    PhotoReport,
    PhotoReportImage,
    UploadedFile,
    utc_now,
)
from app.rag import chunk_sections, parse_document
from app.services.ai import AIOrchestrator, OpenAICompatibleClient
from app.services.ai.media import extract_audio, extract_frames, filter_evidence_frames
from app.services.tasks import TaskContext, TaskDispatcher


def register_workflows(dispatcher: TaskDispatcher) -> None:
    dispatcher.register("inspection_record_generation", inspection_workflow)
    dispatcher.register("photo_report_generation", photo_workflow)
    dispatcher.register("interview_record_generation", interview_workflow)
    dispatcher.register("knowledge_indexing", knowledge_index_workflow)
    dispatcher.register("knowledge_reindexing", knowledge_rebuild_workflow)


def inspection_workflow(context: TaskContext) -> dict[str, Any]:
    task = context.task
    data = task.input_data or {}
    record = _required(context, InspectionRecord, data.get("entity_id"), "INSPECTION_NOT_FOUND")
    source = _required(context, UploadedFile, data.get("file_id"), "SOURCE_FILE_NOT_FOUND")
    settings = context.application_state.settings
    storage = context.application_state.storage
    client = OpenAICompatibleClient(settings)
    orchestrator = AIOrchestrator(client)
    context.update(10, "extracting_media")
    with TemporaryDirectory(prefix="fip-inspection-") as temporary:
        directory = Path(temporary)
        frames = extract_frames(storage.resolve(source.storage_path), directory / "frames", 3)
        transcript = None
        if client.is_configured("speech"):
            audio = extract_audio(storage.resolve(source.storage_path), directory / "audio.wav")
            context.update(35, "transcribing")
            transcript = client.transcribe(audio)
        context.update(55, "analyzing_evidence")
        draft = orchestrator.inspection_draft(frames, transcript, record.source_notes)
    context.update(85, "persisting_draft")
    for field in (
        "title",
        "inspection_unit",
        "inspection_address",
        "contact_person",
        "contact_phone",
        "summary",
        "conclusion",
    ):
        setattr(record, field, _str_or_none(draft.get(field)))
    record.inspector_names = _string_list(draft.get("inspector_names"))
    record.inspection_date = _date_time(draft.get("inspection_date"))
    record.status = "generated"
    context.session.execute(
        delete(InspectionRecordItem).where(InspectionRecordItem.inspection_record_id == record.id)
    )
    for index, item in enumerate(_dict_list(draft.get("findings"))):
        description = _str_or_none(item.get("description"))
        if not description:
            continue
        context.session.add(
            InspectionRecordItem(
                inspection_record_id=record.id,
                item_type=_choice(
                    item.get("item_type"),
                    {"compliant", "violation", "hazard", "observation", "recommendation"},
                    "observation",
                ),
                location=_str_or_none(item.get("location")),
                description=description,
                legal_basis=_str_or_none(item.get("legal_basis")),
                correction_requirement=_str_or_none(item.get("correction_requirement")),
                severity=_choice(item.get("severity"), {"low", "medium", "high", "critical"}, None),
                sort_order=index,
            )
        )
    context.session.commit()
    return {"entity_type": "inspection_record", "entity_id": str(record.id)}


def photo_workflow(context: TaskContext) -> dict[str, Any]:
    data = context.task.input_data or {}
    report = _required(context, PhotoReport, data.get("entity_id"), "PHOTO_REPORT_NOT_FOUND")
    source = _required(context, UploadedFile, data.get("file_id"), "SOURCE_FILE_NOT_FOUND")
    settings = context.application_state.settings
    storage = context.application_state.storage
    orchestrator = AIOrchestrator(OpenAICompatibleClient(settings))
    context.update(10, "extracting_frames")
    with TemporaryDirectory(prefix="fip-photo-") as temporary:
        frames = filter_evidence_frames(
            extract_frames(
                storage.resolve(source.storage_path),
                Path(temporary) / "frames",
                settings.max_video_frames,
            )
        )
        if not frames:
            raise AppError(
                status_code=422,
                code="NO_USABLE_FRAMES",
                message="The video did not contain usable evidence frames.",
            )
        context.session.execute(
            delete(PhotoReportImage).where(PhotoReportImage.photo_report_id == report.id)
        )
        addresses: list[str] = []
        violations: list[str] = []
        for index, frame in enumerate(frames):
            context.update(20 + int(index / len(frames) * 65), "analyzing_frames")
            analysis = orchestrator.photo_evidence(frame)
            with frame.open("rb") as source_stream:
                stored = storage.save(
                    category="key-frames", filename=frame.name, source=source_stream
                )
            uploaded = UploadedFile(
                original_name=frame.name,
                storage_path=stored.path,
                storage_provider="local",
                mime_type="image/jpeg",
                file_extension=".jpg",
                size_bytes=stored.size_bytes,
                checksum=None,
                category="image",
                uploaded_by=report.created_by,
            )
            context.session.add(uploaded)
            context.session.flush()
            address = _str_or_none(analysis.get("detected_address"))
            violation = _str_or_none(analysis.get("detected_violation"))
            if address:
                addresses.append(address)
            if violation:
                violations.append(violation)
            context.session.add(
                PhotoReportImage(
                    photo_report_id=report.id,
                    uploaded_file_id=uploaded.id,
                    frame_timestamp=float(index * 8),
                    caption=_str_or_none(analysis.get("caption")),
                    detected_address=address,
                    detected_violation=violation,
                    is_selected=True,
                    needs_review=bool(analysis.get("needs_review", True)),
                    sort_order=index,
                )
            )
        report.inspection_address = _consistent_value(addresses)
        report.violation_summary = "；".join(dict.fromkeys(violations)) or None
        report.status = "generated"
        context.session.commit()
    return {"entity_type": "photo_report", "entity_id": str(report.id)}


def interview_workflow(context: TaskContext) -> dict[str, Any]:
    data = context.task.input_data or {}
    record = _required(context, InterviewRecord, data.get("entity_id"), "INTERVIEW_NOT_FOUND")
    source = _required(context, UploadedFile, data.get("file_id"), "SOURCE_FILE_NOT_FOUND")
    settings = context.application_state.settings
    storage = context.application_state.storage
    client = OpenAICompatibleClient(settings)
    orchestrator = AIOrchestrator(client)
    context.update(15, "extracting_audio")
    with TemporaryDirectory(prefix="fip-interview-") as temporary:
        audio = extract_audio(storage.resolve(source.storage_path), Path(temporary) / "audio.wav")
        context.update(35, "transcribing")
        transcript = client.transcribe(audio)
        if not transcript.strip():
            raise AppError(
                status_code=422,
                code="NO_AUDIBLE_SPEECH",
                message="No audible speech was detected in the recording.",
            )
        context.update(70, "structuring_transcript")
        draft = orchestrator.interview_draft(transcript)
    record.transcript = transcript
    record.title = _str_or_none(draft.get("title"))
    record.interviewee_name = _str_or_none(draft.get("interviewee_name"))
    record.interviewer_names = _string_list(draft.get("interviewer_names"))
    record.location = _str_or_none(draft.get("location"))
    record.started_at = _date_time(draft.get("started_at"))
    record.ended_at = _date_time(draft.get("ended_at"))
    structured = draft.get("structured_content")
    record.structured_content = structured if isinstance(structured, dict) else {"sections": []}
    record.status = "generated"
    context.session.commit()
    return {"entity_type": "interview_record", "entity_id": str(record.id)}


def knowledge_index_workflow(context: TaskContext) -> dict[str, Any]:
    data = context.task.input_data or {}
    document = _required(
        context, KnowledgeDocument, data.get("document_id"), "KNOWLEDGE_DOCUMENT_NOT_FOUND"
    )
    count = _index_document(context, document)
    return {
        "entity_type": "knowledge_document",
        "entity_id": str(document.id),
        "chunk_count": count,
    }


def knowledge_rebuild_workflow(context: TaskContext) -> dict[str, Any]:
    raw_ids = (context.task.input_data or {}).get("document_ids")
    document_ids = []
    if isinstance(raw_ids, list):
        for value in raw_ids:
            try:
                document_ids.append(uuid.UUID(str(value)))
            except ValueError:
                continue
    documents = context.session.scalars(
        select(KnowledgeDocument).where(
            KnowledgeDocument.deleted_at.is_(None), KnowledgeDocument.id.in_(document_ids)
        )
    ).all()
    total_chunks = 0
    for index, document in enumerate(documents):
        context.update(5 + int(index / max(1, len(documents)) * 90), "rebuilding_index")
        total_chunks += _index_document(context, document, update_task=False)
    return {"entity_type": "knowledge_index", "documents": len(documents), "chunks": total_chunks}


def _index_document(
    context: TaskContext, document: KnowledgeDocument, *, update_task: bool = True
) -> int:
    storage = context.application_state.storage
    settings = context.application_state.settings
    source = context.session.get(UploadedFile, document.uploaded_file_id)
    if source is None:
        raise AppError(
            status_code=404,
            code="SOURCE_FILE_NOT_FOUND",
            message="The knowledge source file no longer exists.",
        )
    job = KnowledgeIndexJob(
        knowledge_document_id=document.id,
        ai_task_id=context.task.id,
        action="reindex" if document.chunk_count else "index",
        status="processing",
    )
    context.session.add(job)
    document.status = "parsing"
    document.error_message = None
    context.session.commit()
    try:
        if update_task:
            context.update(20, "parsing_document")
        sections = parse_document(storage.resolve(source.storage_path), source.file_extension or "")
        chunks = chunk_sections(sections, size=settings.chunk_size, overlap=settings.chunk_overlap)
        if not chunks:
            raise AppError(
                status_code=422,
                code="DOCUMENT_HAS_NO_TEXT",
                message="No indexable text was found in the document.",
            )
        document.status = "indexing"
        context.session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_document_id == document.id)
        )
        client = OpenAICompatibleClient(settings)
        embeddings: list[list[float] | None] = [None] * len(chunks)
        if client.is_configured("embedding"):
            for start in range(0, len(chunks), 32):
                batch = [content for content, _ in chunks[start : start + 32]]
                values = client.embed(batch)
                embeddings[start : start + len(values)] = values
        for index, ((content, metadata), embedding) in enumerate(
            zip(chunks, embeddings, strict=True)
        ):
            context.session.add(
                KnowledgeChunk(
                    knowledge_document_id=document.id,
                    chunk_index=index,
                    content=content,
                    embedding=embedding,
                    chunk_metadata=metadata,
                )
            )
        document.status = "indexed"
        document.chunk_count = len(chunks)
        document.updated_at = utc_now()
        job.status = "completed"
        job.indexed_chunks = len(chunks)
        job.completed_at = utc_now()
        context.session.commit()
        if update_task:
            context.update(90, "index_committed")
        return len(chunks)
    except AppError as error:
        document.status = "failed"
        document.error_message = error.message
        job.status = "failed"
        job.error_message = error.message
        job.completed_at = utc_now()
        context.session.commit()
        raise


def _required(context: TaskContext, model: type[Any], value: object, code: str) -> Any:
    try:
        identifier = uuid.UUID(str(value))
    except (TypeError, ValueError) as error:
        raise AppError(
            status_code=404, code=code, message="The task input is no longer available."
        ) from error
    result = context.session.get(model, identifier)
    if result is None:
        raise AppError(status_code=404, code=code, message="The task input is no longer available.")
    return result


def _str_or_none(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _string_list(value: object) -> list[str]:
    return (
        [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if isinstance(value, list)
        else []
    )


def _dict_list(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _choice(value: object, allowed: set[str], fallback: str | None) -> str | None:
    return value if isinstance(value, str) and value in allowed else fallback


def _date_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _consistent_value(values: list[str]) -> str | None:
    unique = list(dict.fromkeys(values))
    return unique[0] if len(unique) == 1 else None
