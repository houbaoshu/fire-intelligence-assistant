"""检查记录生成管线（ARCHITECTURE.md §11 / AI_CONTEXT.md Inspection Record Generation）。

链路：视频 → 抽帧+抽音频 → 语音转写 ∥ 视觉分析 → OCR 帧内文字 →
证据归一化 → LLM 结构化抽取 → 草稿落库（inspection_records + items）。

降级策略：单帧视觉/OCR 失败、无音频轨、音频抽取失败均记录 warning 并继续；
LLM 输出非结构化 JSON 按任务失败处理（禁止编造结构化结果）。
"""

from app.core.config import get_settings
from app.models.inspection import ITEM_TYPES, SEVERITIES
from app.prompts.inspection import (
    INSPECTION_EXTRACT_SYSTEM_PROMPT,
    build_inspection_extract_user_prompt,
)
from app.prompts.photo import PHOTO_FRAME_ANALYSIS_PROMPT
from app.services.ai.llm import LLMService
from app.services.ai.ocr import OCRService
from app.services.ai.providers import AIProviders
from app.services.ai.speech import SpeechService
from app.services.ai.vision import VisionService
from app.services.media import (
    MediaProcessingError,
    MediaWorkspace,
    extract_audio,
    extract_frames,
    select_key_frames,
)
from app.services.pipelines.base import (
    GenerationPipeline,
    PipelineContext,
    PipelineError,
    PipelineResult,
)
from app.services.pipelines.common import (
    load_source_bytes,
    media_failed,
    next_record_number,
    parse_datetime,
    parse_llm_json,
    warn,
)
from app.services.storage import get_storage_service

_NO_USABLE_FRAMES = (
    "NO_USABLE_FRAMES",
    "视频未抽取到可用画面帧，请确认视频内容后重试",
)


def _brief(exc: Exception) -> str:
    message = getattr(exc, "message", None) or str(exc) or type(exc).__name__
    return message[:200]


def _str_list(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    items = [str(v).strip() for v in value if str(v).strip()]
    return items or None


class InspectionRecordPipeline(GenerationPipeline):
    """检查记录：视频分析 → 语音转写 → OCR → 证据归一化 → LLM 抽取 → 草稿。"""

    record_kind = "inspection_record"
    required_capabilities = ("vision", "ocr", "speech", "llm")
    stages = (
        ("video_analysis", 10),
        ("speech_transcription", 30),
        ("ocr", 45),
        ("evidence_normalization", 60),
        ("llm_extract", 80),
        ("draft", 95),
    )

    def execute_stage(
        self, stage: str, ctx: PipelineContext, providers: AIProviders
    ) -> PipelineResult | None:
        handler = {
            "video_analysis": self._video_analysis,
            "speech_transcription": self._speech_transcription,
            "ocr": self._ocr,
            "evidence_normalization": self._evidence_normalization,
            "llm_extract": self._llm_extract,
            "draft": self._draft,
        }[stage]
        return handler(ctx)

    # ---------- 阶段实现 ----------

    def _video_analysis(self, ctx: PipelineContext) -> None:
        """抽帧 + 质量筛选 + 抽音频 + 逐帧视觉分析。"""
        settings = get_settings()
        storage = get_storage_service()
        source_file, video_bytes = load_source_bytes(ctx, storage)

        with MediaWorkspace(ctx.task_id) as workspace:
            video_path = workspace.path("source" + (source_file.file_extension or ".mp4"))
            video_path.write_bytes(video_bytes)
            try:
                frames = extract_frames(
                    video_path,
                    workspace.path("frames"),
                    interval_seconds=settings.MEDIA_FRAME_INTERVAL_SECONDS,
                    max_frames=settings.MEDIA_MAX_KEY_FRAMES,
                )
                key_frames, dropped = select_key_frames(
                    frames, max_frames=settings.MEDIA_MAX_KEY_FRAMES
                )
                audio_path = workspace.path("audio.wav")
                has_audio = extract_audio(video_path, audio_path)
            except MediaProcessingError as exc:
                raise media_failed(exc, "视频处理失败")
            for frame, reason in dropped:
                warn(ctx, f"{frame.timestamp:.1f}s 帧被筛除：{reason}")
            if not key_frames:
                raise PipelineError(*_NO_USABLE_FRAMES)
            ctx.artifacts["key_frames"] = key_frames
            if has_audio:
                ctx.artifacts["audio_bytes"] = audio_path.read_bytes()
            else:
                warn(ctx, "视频不含可抽取的音频轨，语音转写跳过")

        # 逐帧视觉分析：单帧失败降级（warning 留痕），不中断整体流程
        vision = VisionService()
        analyses = []
        for frame in key_frames:
            try:
                text = vision.analyze_image(
                    PHOTO_FRAME_ANALYSIS_PROMPT, image_bytes=frame.data
                )
                analyses.append({"timestamp": frame.timestamp, "analysis": text})
            except Exception as exc:
                warn(ctx, f"{frame.timestamp:.1f}s 帧视觉分析失败：{_brief(exc)}")
        if not analyses:
            raise PipelineError(
                "VISION_ANALYSIS_FAILED",
                "全部帧的视觉分析均失败，无法形成检查证据，请重试",
            )
        ctx.artifacts["frame_analyses"] = analyses

    def _speech_transcription(self, ctx: PipelineContext) -> None:
        """语音转写；无音频轨或转写失败时降级跳过（warning 留痕）。"""
        audio = ctx.artifacts.get("audio_bytes")
        if not audio:
            ctx.artifacts["transcript"] = None
            return
        try:
            ctx.artifacts["transcript"] = SpeechService().transcribe(
                audio, filename="audio.wav"
            )
        except Exception as exc:
            warn(ctx, f"语音转写失败：{_brief(exc)}")
            ctx.artifacts["transcript"] = None

    def _ocr(self, ctx: PipelineContext) -> None:
        """逐帧 OCR；单帧失败降级（warning 留痕）。"""
        ocr = OCRService()
        texts = []
        for frame in ctx.artifacts["key_frames"]:
            try:
                text = ocr.extract_text(frame.data)
            except Exception as exc:
                warn(ctx, f"{frame.timestamp:.1f}s 帧 OCR 失败：{_brief(exc)}")
                continue
            if text:
                texts.append({"timestamp": frame.timestamp, "text": text})
        ctx.artifacts["ocr_texts"] = texts

    def _evidence_normalization(self, ctx: PipelineContext) -> None:
        """证据归一化：合并视觉分析、OCR 与转写为统一证据结构（纯机械处理）。"""
        ctx.artifacts["evidence"] = {
            "frame_analyses": ctx.artifacts.get("frame_analyses", []),
            "ocr_texts": ctx.artifacts.get("ocr_texts", []),
            "transcript": ctx.artifacts.get("transcript"),
        }

    def _llm_extract(self, ctx: PipelineContext) -> None:
        """LLM 综合产出结构化 JSON；解析失败按任务失败处理。"""
        evidence = ctx.artifacts["evidence"]
        content = LLMService().chat(
            [
                {"role": "system", "content": INSPECTION_EXTRACT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_inspection_extract_user_prompt(
                        frame_analyses=evidence["frame_analyses"],
                        ocr_texts=evidence["ocr_texts"],
                        transcript=evidence["transcript"],
                        remarks=ctx.remarks,
                    ),
                },
            ]
        )
        ctx.artifacts["draft_json"] = parse_llm_json(content, stage="llm_extract")

    def _draft(self, ctx: PipelineContext) -> PipelineResult:
        """组装落库结构：字段 + items（枚举过滤，非法项丢弃并留痕）。"""
        data = ctx.artifacts["draft_json"]
        items = []
        for raw in data.get("items") or []:
            description = str(raw.get("description") or "").strip() if isinstance(raw, dict) else ""
            if not description:
                warn(ctx, "丢弃一条缺少描述的检查项（LLM 输出不完整）")
                continue
            item_type = str(raw.get("item_type") or "")
            if item_type not in ITEM_TYPES:
                warn(ctx, f"丢弃一条 item_type 非法（{item_type or '空'}）的检查项")
                continue
            severity = str(raw.get("severity") or "") or None
            if severity is not None and severity not in SEVERITIES:
                warn(ctx, f"检查项 severity 非法（{severity}），置空待人工补充")
                severity = None
            items.append(
                {
                    "item_type": item_type,
                    "location": str(raw.get("location") or "") or None,
                    "description": description,
                    "legal_basis": str(raw.get("legal_basis") or "") or None,
                    "correction_requirement": str(raw.get("correction_requirement") or "")
                    or None,
                    "severity": severity,
                    "sort_order": len(items) + 1,
                }
            )
        fields = {
            "record_number": next_record_number(),
            "title": str(data.get("title") or "") or None,
            "inspection_unit": str(data.get("inspection_unit") or "") or None,
            "inspection_address": str(data.get("inspection_address") or "") or None,
            "inspection_date": parse_datetime(data.get("inspection_date")),
            "inspector_names": _str_list(data.get("inspector_names")),
            "contact_person": str(data.get("contact_person") or "") or None,
            "contact_phone": str(data.get("contact_phone") or "") or None,
            "summary": str(data.get("summary") or "") or None,
            "conclusion": str(data.get("conclusion") or "") or None,
            "source_task_id": ctx.task_id,
        }
        return PipelineResult(
            fields=fields, items=items, warnings=ctx.artifacts.get("warnings", [])
        )
