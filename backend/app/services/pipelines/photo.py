"""拍照报告生成管线（ARCHITECTURE.md §12 / AI_CONTEXT.md Photo Report Generation）。

链路：视频 → 候选帧抽取 → 去重/质量筛选 → 逐帧视觉分析 → OCR →
LLM 生成 caption 与报告级 JSON → 落库（photo_reports + photo_report_images）。

关键帧存对象存储 ``key-frames/`` 并登记 uploaded_files（category=image），
供 photo_report_images 引用；``is_selected`` 默认 True，``frame_timestamp``
记录源视频秒数。单帧分析失败降级（warning 留痕），不静默丢弃。
"""

from app.core.config import get_settings
from app.prompts.photo import build_photo_report_user_prompt
from app.services.ai.llm import LLMService
from app.services.ai.ocr import OCRService
from app.services.ai.providers import AIProviders
from app.services.ai.vision import VisionService
from app.services.media import (
    MediaProcessingError,
    MediaWorkspace,
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
    parse_llm_json,
    register_key_frame,
    warn,
)
from app.services.prompt_service import get_prompt
from app.services.storage import get_storage_service


def _brief(exc: Exception) -> str:
    message = getattr(exc, "message", None) or str(exc) or type(exc).__name__
    return message[:200]


class PhotoReportPipeline(GenerationPipeline):
    """拍照报告：抽帧 → 去重筛选 → 视觉分析 → OCR → LLM 抽取 → 草稿。"""

    record_kind = "photo_report"
    required_capabilities = ("vision", "ocr", "llm")
    stages = (
        ("frame_extraction", 15),
        ("frame_dedup", 30),
        ("vision_analysis", 55),
        ("ocr", 70),
        ("llm_extract", 85),
        ("draft", 95),
    )

    def execute_stage(
        self, stage: str, ctx: PipelineContext, providers: AIProviders
    ) -> PipelineResult | None:
        handler = {
            "frame_extraction": self._frame_extraction,
            "frame_dedup": self._frame_dedup,
            "vision_analysis": self._vision_analysis,
            "ocr": self._ocr,
            "llm_extract": self._llm_extract,
            "draft": self._draft,
        }[stage]
        return handler(ctx)

    # ---------- 阶段实现 ----------

    def _frame_extraction(self, ctx: PipelineContext) -> None:
        """从视频中按间隔抽取候选帧。"""
        settings = get_settings()
        storage = get_storage_service()
        source_file, video_bytes = load_source_bytes(ctx, storage)
        ctx.artifacts["uploaded_by"] = source_file.uploaded_by

        with MediaWorkspace(ctx.task_id) as workspace:
            video_path = workspace.path("source" + (source_file.file_extension or ".mp4"))
            video_path.write_bytes(video_bytes)
            try:
                # 候选帧抽取放宽松（上限 4 倍），留给去重/质量筛选裁决
                frames = extract_frames(
                    video_path,
                    workspace.path("frames"),
                    interval_seconds=settings.MEDIA_FRAME_INTERVAL_SECONDS,
                    max_frames=settings.MEDIA_MAX_KEY_FRAMES * 4,
                )
            except MediaProcessingError as exc:
                raise media_failed(exc, "视频抽帧失败")
        if not frames:
            raise PipelineError(
                "NO_USABLE_FRAMES", "视频未抽取到任何画面帧，请确认视频内容后重试"
            )
        ctx.artifacts["candidate_frames"] = frames

    def _frame_dedup(self, ctx: PipelineContext) -> None:
        """去重 + 模糊筛选；保留帧落对象存储并登记 uploaded_files。"""
        settings = get_settings()
        storage = get_storage_service()
        kept, dropped = select_key_frames(
            ctx.artifacts["candidate_frames"], max_frames=settings.MEDIA_MAX_KEY_FRAMES
        )
        for frame, reason in dropped:
            warn(ctx, f"{frame.timestamp:.1f}s 候选帧被筛除：{reason}")
        if not kept:
            raise PipelineError(
                "NO_USABLE_FRAMES", "全部候选帧均被质量筛选排除，请更换视频后重试"
            )
        key_frames = []
        for index, frame in enumerate(kept):
            file_id = register_key_frame(
                frame_data=frame.data,
                uploaded_by=ctx.artifacts["uploaded_by"],
                storage=storage,
            )
            key_frames.append(
                {
                    "index": index,
                    "timestamp": frame.timestamp,
                    "data": frame.data,
                    "file_id": file_id,
                }
            )
        ctx.artifacts["key_frames"] = key_frames

    def _vision_analysis(self, ctx: PipelineContext) -> None:
        """逐帧视觉分析（地址/违规/画面描述）；单帧失败降级并标记缺失分析。"""
        vision = VisionService()
        for frame in ctx.artifacts["key_frames"]:
            try:
                text = vision.analyze_image(
                    get_prompt("photo.FRAME_ANALYSIS"), image_bytes=frame["data"]
                )
                result = parse_llm_json(text, stage="vision_analysis")
            except PipelineError:
                warn(ctx, f"{frame['timestamp']:.1f}s 帧视觉分析结果无法解析，标记缺失")
                result = None
            except Exception as exc:
                warn(ctx, f"{frame['timestamp']:.1f}s 帧视觉分析失败：{_brief(exc)}")
                result = None
            frame["analysis"] = result

    def _ocr(self, ctx: PipelineContext) -> None:
        """逐帧 OCR（地址旁证）；单帧失败降级。"""
        ocr = OCRService()
        for frame in ctx.artifacts["key_frames"]:
            try:
                frame["ocr_text"] = ocr.extract_text(frame["data"])
            except Exception as exc:
                warn(ctx, f"{frame['timestamp']:.1f}s 帧 OCR 失败：{_brief(exc)}")
                frame["ocr_text"] = ""

    def _llm_extract(self, ctx: PipelineContext) -> None:
        """LLM 汇总产出报告级 JSON 与逐帧 caption。"""
        frame_results = []
        for frame in ctx.artifacts["key_frames"]:
            analysis = frame.get("analysis") or {}
            frame_results.append(
                {
                    "frame_index": frame["index"],
                    "timestamp": frame["timestamp"],
                    "detected_address": analysis.get("detected_address") or "",
                    "detected_violation": analysis.get("detected_violation") or "",
                    "description": analysis.get("description") or "",
                    "ocr_text": frame.get("ocr_text") or "",
                }
            )
        content = LLMService().chat(
            [
                {"role": "system", "content": get_prompt("photo.REPORT_SYSTEM")},
                {
                    "role": "user",
                    "content": build_photo_report_user_prompt(
                        frame_results=frame_results, remarks=ctx.remarks
                    ),
                },
            ]
        )
        ctx.artifacts["draft_json"] = parse_llm_json(content, stage="llm_extract")

    def _draft(self, ctx: PipelineContext) -> PipelineResult:
        """组装落库结构：报告字段 + images（caption 按 frame_index 对齐）。"""
        data = ctx.artifacts["draft_json"]
        captions: dict[int, str] = {}
        for raw in data.get("captions") or []:
            if isinstance(raw, dict) and isinstance(raw.get("frame_index"), int):
                caption = str(raw.get("caption") or "").strip()
                if caption:
                    captions[raw["frame_index"]] = caption
        missing = [
            f["index"] for f in ctx.artifacts["key_frames"] if f["index"] not in captions
        ]
        if missing:
            warn(ctx, f"帧序号 {missing} 缺少 LLM caption，留空待人工补充")

        images = []
        for frame in ctx.artifacts["key_frames"]:
            analysis = frame.get("analysis") or {}
            images.append(
                {
                    "uploaded_file_id": frame["file_id"],
                    "frame_timestamp": frame["timestamp"],
                    "caption": captions.get(frame["index"]),
                    "detected_address": str(analysis.get("detected_address") or "")
                    or None,
                    "detected_violation": str(analysis.get("detected_violation") or "")
                    or None,
                    "is_selected": True,
                    "sort_order": frame["index"] + 1,
                }
            )
        fields = {
            "title": str(data.get("title") or "") or None,
            "inspection_unit": str(data.get("inspection_unit") or "") or None,
            "inspection_address": str(data.get("inspection_address") or "") or None,
            "violation_summary": str(data.get("violation_summary") or "") or None,
            "source_task_id": ctx.task_id,
        }
        return PipelineResult(
            fields=fields, images=images, warnings=ctx.artifacts.get("warnings", [])
        )
