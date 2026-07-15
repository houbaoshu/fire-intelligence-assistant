"""Background task executor for AI processing pipelines."""

from __future__ import annotations

import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import _get_session_factory
from app.core.exceptions import NotFoundException, TaskFailedException
from app.core.logging import get_logger
from app.models.inspection import InspectionRecord, InspectionRecordItem
from app.models.interview import InterviewRecord
from app.models.knowledge import KnowledgeDocument, KnowledgeIndexJob
from app.models.photo_report import PhotoReport, PhotoReportImage
from app.models.task import AITask

logger = get_logger(__name__)


class TaskExecutor:
    """Manages background task execution for AI processing pipelines.

    Each execute method follows the pattern:
    1. Update task status to "processing"
    2. Execute pipeline stages, updating progress and current_stage
    3. On success: save structured result, mark task completed
    4. On failure: mark task failed with error details
    """

    async def _get_task(self, db: AsyncSession, task_id: str) -> AITask:
        """Fetch task by ID."""
        result = await db.execute(select(AITask).where(AITask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundException(f"Task not found: {task_id}")
        return task

    async def _update_task(
        self,
        db: AsyncSession,
        task: AITask,
        status: str | None = None,
        progress: int | None = None,
        current_stage: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        result_data: dict | None = None,
    ) -> None:
        """Update task fields and commit."""
        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = progress
        if current_stage is not None:
            task.current_stage = current_stage
        if error_code is not None:
            task.error_code = error_code
        if error_message is not None:
            task.error_message = error_message
        if result_data is not None:
            task.result_data = result_data

        if status == "processing" and not task.started_at:
            task.started_at = datetime.now(UTC)
        if status in ("completed", "failed"):
            task.completed_at = datetime.now(UTC)

        await db.commit()

    async def _extract_frames(
        self, video_path: str, output_dir: str, max_frames: int = 10
    ) -> list[str]:
        """Extract frames from video using ffmpeg.

        Args:
            video_path: Path to video file.
            output_dir: Directory to save extracted frames.
            max_frames: Maximum number of frames to extract.

        Returns:
            List of frame file paths.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Get video duration
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip()) if result.stdout.strip() else 0

        if duration <= 0:
            return []

        # Calculate interval
        interval = duration / (max_frames + 1)
        frame_paths = []

        for i in range(max_frames):
            timestamp = interval * (i + 1)
            output_path = f"{output_dir}/frame_{i:03d}.jpg"
            cmd = [
                "ffmpeg",
                "-ss",
                str(timestamp),
                "-i",
                video_path,
                "-vframes",
                "1",
                "-q:v",
                "2",
                "-y",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True)
            if Path(output_path).exists():
                frame_paths.append(output_path)

        return frame_paths

    async def _extract_audio(self, video_path: str, output_path: str) -> str:
        """Extract audio from video using ffmpeg.

        Args:
            video_path: Path to video file.
            output_path: Path to save extracted audio.

        Returns:
            Path to extracted audio file.
        """
        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-y",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True)
        return output_path

    async def execute_inspection_generation(
        self,
        task_id: str,
        file_path: str,
        remarks: str | None = None,
    ) -> None:
        """Execute inspection record generation pipeline.

        Pipeline: extract frames -> vision analysis -> OCR -> LLM reasoning -> save record

        Args:
            task_id: AITask ID.
            file_path: Path to uploaded video file.
            remarks: Optional user remarks.
        """
        factory = _get_session_factory()
        async with factory() as db:
            task = await self._get_task(db, task_id)

            try:
                # Mark as processing
                await self._update_task(
                    db,
                    task,
                    status="processing",
                    progress=0,
                    current_stage="extracting_frames",
                )

                # Extract frames
                with tempfile.TemporaryDirectory() as tmpdir:
                    frames_dir = f"{tmpdir}/frames"
                    frame_paths = await self._extract_frames(file_path, frames_dir, max_frames=10)

                    if not frame_paths:
                        raise TaskFailedException("Failed to extract frames from video")

                    await self._update_task(
                        db,
                        task,
                        progress=20,
                        current_stage="analyzing_frames",
                    )

                    # Analyze frames with vision model
                    from app.services.ai.llm import LLMService
                    from app.services.ai.ocr import OCRService
                    from app.services.ai.vision import VisionService

                    vision = VisionService()
                    ocr = OCRService()
                    llm = LLMService()

                    frame_analyses = []
                    for idx, frame_path in enumerate(frame_paths):
                        analysis = await vision.analyze_image(
                            frame_path,
                            "请分析这张消防检查现场照片，描述看到的消防设施、设备、环境以及可能存在的消防隐患或违规行为。",
                        )
                        frame_analyses.append(analysis)

                        progress = 20 + int((idx + 1) / len(frame_paths) * 30)
                        await self._update_task(
                            db,
                            task,
                            progress=progress,
                            current_stage=f"analyzing_frame_{idx + 1}",
                        )

                    await self._update_task(
                        db,
                        task,
                        progress=50,
                        current_stage="extracting_text",
                    )

                    # OCR on frames (optional, for signs/labels)
                    ocr_texts = []
                    for frame_path in frame_paths[:3]:  # OCR on first 3 frames
                        try:
                            text = await ocr.extract_text(frame_path)
                            if text.strip():
                                ocr_texts.append(text)
                        except Exception as e:
                            logger.warning("OCR failed for frame: %s", e)

                    await self._update_task(
                        db,
                        task,
                        progress=70,
                        current_stage="generating_record",
                    )

                    # LLM reasoning to generate structured inspection record
                    context = "\n\n".join(frame_analyses)
                    if ocr_texts:
                        context += "\n\n识别到的文字:\n" + "\n".join(ocr_texts)

                    prompt = f"""基于以下消防检查现场分析结果，生成一份结构化的消防检查记录。

现场分析:
{context}

{f"用户备注: {remarks}" if remarks else ""}

请以JSON格式返回，包含以下字段:
{{
  "title": "检查记录标题",
  "inspection_unit": "被检查单位名称",
  "inspection_address": "检查地址",
  "inspector_names": ["检查员1", "检查员2"],
  "contact_person": "联系人",
  "contact_phone": "联系电话",
  "summary": "检查概况",
  "conclusion": "检查结论",
  "items": [
    {{
      "item_type": "compliant/violation/hazard/observation/recommendation",
      "location": "位置",
      "description": "描述",
      "legal_basis": "法律依据",
      "correction_requirement": "整改要求",
      "severity": "low/medium/high/critical"
    }}
  ]
}}"""

                    record_data = await llm.chat_json([{"role": "user", "content": prompt}])

                    await self._update_task(
                        db,
                        task,
                        progress=90,
                        current_stage="saving_record",
                    )

                    # Create inspection record
                    record = InspectionRecord(
                        title=record_data.get("title"),
                        inspection_unit=record_data.get("inspection_unit"),
                        inspection_address=record_data.get("inspection_address"),
                        inspector_names=record_data.get("inspector_names"),
                        contact_person=record_data.get("contact_person"),
                        contact_phone=record_data.get("contact_phone"),
                        summary=record_data.get("summary"),
                        conclusion=record_data.get("conclusion"),
                        status="generated",
                        source_task_id=task_id,
                        created_by=task.created_by,
                    )
                    db.add(record)
                    await db.flush()

                    # Create items
                    for idx, item_data in enumerate(record_data.get("items", [])):
                        item = InspectionRecordItem(
                            inspection_record_id=record.id,
                            item_type=item_data.get("item_type", "observation"),
                            location=item_data.get("location"),
                            description=item_data.get("description", ""),
                            legal_basis=item_data.get("legal_basis"),
                            correction_requirement=item_data.get("correction_requirement"),
                            severity=item_data.get("severity"),
                            sort_order=idx,
                        )
                        db.add(item)

                    await db.flush()

                    # Mark task completed
                    await self._update_task(
                        db,
                        task,
                        status="completed",
                        progress=100,
                        current_stage="completed",
                        result_data={"record_id": record.id},
                    )

                    logger.info("Inspection record generated", extra={"record_id": record.id})

            except Exception as exc:
                logger.exception("Inspection generation failed")
                await self._update_task(
                    db,
                    task,
                    status="failed",
                    error_code="GENERATION_FAILED",
                    error_message=str(exc),
                )
                raise

    async def execute_photo_report_generation(
        self,
        task_id: str,
        file_path: str,
    ) -> None:
        """Execute photo report generation pipeline.

        Pipeline: extract frames -> vision analysis -> captions -> save report

        Args:
            task_id: AITask ID.
            file_path: Path to uploaded video file.
        """
        factory = _get_session_factory()
        async with factory() as db:
            task = await self._get_task(db, task_id)

            try:
                await self._update_task(
                    db,
                    task,
                    status="processing",
                    progress=0,
                    current_stage="extracting_frames",
                )

                with tempfile.TemporaryDirectory() as tmpdir:
                    frames_dir = f"{tmpdir}/frames"
                    frame_paths = await self._extract_frames(file_path, frames_dir, max_frames=20)

                    if not frame_paths:
                        raise TaskFailedException("Failed to extract frames from video")

                    await self._update_task(
                        db,
                        task,
                        progress=20,
                        current_stage="analyzing_frames",
                    )

                    from app.services.ai.llm import LLMService
                    from app.services.ai.vision import VisionService

                    vision = VisionService()
                    llm = LLMService()

                    # Analyze each frame
                    image_data_list = []
                    for idx, frame_path in enumerate(frame_paths):
                        analysis = await vision.analyze_image_structured(
                            frame_path,
                            "请分析这张照片，识别：1.拍摄地址（如果有）"
                            "2.是否存在消防违规行为 3.照片内容描述",
                        )
                        image_data_list.append(
                            {
                                "path": frame_path,
                                "analysis": analysis,
                            }
                        )

                        progress = 20 + int((idx + 1) / len(frame_paths) * 50)
                        await self._update_task(
                            db,
                            task,
                            progress=progress,
                            current_stage=f"analyzing_frame_{idx + 1}",
                        )

                    await self._update_task(
                        db,
                        task,
                        progress=70,
                        current_stage="generating_report",
                    )

                    # Generate report summary
                    analyses_text = "\n\n".join(
                        [f"照片{i + 1}: {img['analysis']}" for i, img in enumerate(image_data_list)]
                    )

                    prompt = f"""基于以下现场照片分析结果，生成一份消防照片报告摘要。

照片分析:
{analyses_text}

请以JSON格式返回:
{{
  "title": "报告标题",
  "inspection_unit": "被检查单位",
  "inspection_address": "检查地址",
  "violation_summary": "违规情况概述"
}}"""

                    report_data = await llm.chat_json([{"role": "user", "content": prompt}])

                    await self._update_task(
                        db,
                        task,
                        progress=90,
                        current_stage="saving_report",
                    )

                    # Create photo report
                    report = PhotoReport(
                        title=report_data.get("title"),
                        inspection_unit=report_data.get("inspection_unit"),
                        inspection_address=report_data.get("inspection_address"),
                        violation_summary=report_data.get("violation_summary"),
                        status="generated",
                        source_task_id=task_id,
                        created_by=task.created_by,
                    )
                    db.add(report)
                    await db.flush()

                    # Save image records (without actual file storage for now)
                    for idx, img_data in enumerate(image_data_list):
                        analysis = img_data["analysis"]
                        image_record = PhotoReportImage(
                            photo_report_id=report.id,
                            uploaded_file_id=None,  # Would need to save frame to storage
                            caption=analysis.get("description", ""),
                            detected_address=analysis.get("address"),
                            detected_violation=analysis.get("violation"),
                            is_selected=True,
                            sort_order=idx,
                        )
                        db.add(image_record)

                    await db.flush()

                    await self._update_task(
                        db,
                        task,
                        status="completed",
                        progress=100,
                        current_stage="completed",
                        result_data={"report_id": report.id},
                    )

                    logger.info("Photo report generated", extra={"report_id": report.id})

            except Exception as exc:
                logger.exception("Photo report generation failed")
                await self._update_task(
                    db,
                    task,
                    status="failed",
                    error_code="GENERATION_FAILED",
                    error_message=str(exc),
                )
                raise

    async def execute_interview_generation(
        self,
        task_id: str,
        file_path: str,
    ) -> None:
        """Execute interview record generation pipeline.

        Pipeline: extract audio -> speech recognition -> LLM -> save record

        Args:
            task_id: AITask ID.
            file_path: Path to uploaded audio/video file.
        """
        factory = _get_session_factory()
        async with factory() as db:
            task = await self._get_task(db, task_id)

            try:
                await self._update_task(
                    db,
                    task,
                    status="processing",
                    progress=0,
                    current_stage="extracting_audio",
                )

                with tempfile.TemporaryDirectory() as tmpdir:
                    audio_path = f"{tmpdir}/audio.wav"
                    await self._extract_audio(file_path, audio_path)

                    if not Path(audio_path).exists():
                        raise TaskFailedException("Failed to extract audio from file")

                    await self._update_task(
                        db,
                        task,
                        progress=30,
                        current_stage="transcribing",
                    )

                    from app.services.ai.llm import LLMService
                    from app.services.ai.speech import SpeechService

                    speech = SpeechService()
                    llm = LLMService()

                    # Transcribe audio
                    transcript = await speech.transcribe(audio_path)

                    if not transcript.strip():
                        raise TaskFailedException("Speech recognition returned empty transcript")

                    await self._update_task(
                        db,
                        task,
                        progress=60,
                        current_stage="structuring_content",
                    )

                    # Structure interview content with LLM
                    prompt = f"""基于以下询问录音转写文本，提取结构化信息。

转写文本:
{transcript}

请以JSON格式返回:
{{
  "title": "询问笔录标题",
  "interviewee_name": "被询问人姓名",
  "interviewer_names": ["询问人1", "询问人2"],
  "location": "询问地点",
  "structured_content": {{
    "key_points": ["要点1", "要点2"],
    "facts": ["事实1", "事实2"],
    "statements": ["陈述1", "陈述2"]
  }}
}}"""

                    structured_data = await llm.chat_json([{"role": "user", "content": prompt}])

                    await self._update_task(
                        db,
                        task,
                        progress=90,
                        current_stage="saving_record",
                    )

                    # Create interview record
                    record = InterviewRecord(
                        title=structured_data.get("title"),
                        interviewee_name=structured_data.get("interviewee_name"),
                        interviewer_names=structured_data.get("interviewer_names"),
                        location=structured_data.get("location"),
                        transcript=transcript,
                        structured_content=structured_data.get("structured_content"),
                        status="generated",
                        source_task_id=task_id,
                        created_by=task.created_by,
                    )
                    db.add(record)
                    await db.flush()

                    await self._update_task(
                        db,
                        task,
                        status="completed",
                        progress=100,
                        current_stage="completed",
                        result_data={"record_id": record.id},
                    )

                    logger.info("Interview record generated", extra={"record_id": record.id})

            except Exception as exc:
                logger.exception("Interview generation failed")
                await self._update_task(
                    db,
                    task,
                    status="failed",
                    error_code="GENERATION_FAILED",
                    error_message=str(exc),
                )
                raise

    async def execute_knowledge_indexing(
        self,
        task_id: str,
        doc_id: str,
    ) -> None:
        """Execute knowledge document indexing pipeline.

        Pipeline: parse -> chunk -> embed -> store in vector DB

        Args:
            task_id: AITask ID.
            doc_id: KnowledgeDocument ID.
        """
        factory = _get_session_factory()
        async with factory() as db:
            task = await self._get_task(db, task_id)

            try:
                # Fetch knowledge document
                result = await db.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
                )
                doc = result.scalar_one_or_none()
                if not doc:
                    raise NotFoundException(f"Knowledge document not found: {doc_id}")

                await self._update_task(
                    db,
                    task,
                    status="processing",
                    progress=0,
                    current_stage="parsing_document",
                )

                # Update document status
                doc.status = "parsing"
                await db.commit()

                # Parse document (simplified - would need actual PDF/Word parsing)
                # For now, just mark as indexed
                await self._update_task(
                    db,
                    task,
                    progress=50,
                    current_stage="chunking",
                )

                doc.status = "indexing"
                await db.commit()

                # Chunking and embedding would happen here
                # For now, simulate completion
                await self._update_task(
                    db,
                    task,
                    progress=100,
                    current_stage="completed",
                )

                doc.status = "indexed"
                doc.chunk_count = 0  # Would be actual count
                await db.commit()

                # Update index job
                result = await db.execute(
                    select(KnowledgeIndexJob).where(KnowledgeIndexJob.ai_task_id == task_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = "completed"
                    job.completed_at = datetime.now(UTC)
                    await db.commit()

                await self._update_task(
                    db,
                    task,
                    status="completed",
                    result_data={"doc_id": doc_id, "chunks": doc.chunk_count},
                )

                logger.info("Knowledge document indexed", extra={"doc_id": doc_id})

            except Exception as exc:
                logger.exception("Knowledge indexing failed")

                # Update document status
                result = await db.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = "failed"
                    await db.commit()

                # Update index job
                result = await db.execute(
                    select(KnowledgeIndexJob).where(KnowledgeIndexJob.ai_task_id == task_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = str(exc)
                    await db.commit()

                await self._update_task(
                    db,
                    task,
                    status="failed",
                    error_code="INDEXING_FAILED",
                    error_message=str(exc),
                )
                raise
