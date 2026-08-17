"""询问记录生成管线（ARCHITECTURE.md §13 / AI_CONTEXT.md Interview Record Generation）。

链路：音频 → 语音转写 → 转写清洗 → 说话人分离（LLM 中性标签）→
LLM 结构化抽取 → 落库（interview_records）。

契约：原始机器转写与结构化内容分开保存 —— ``transcript`` 列存清洗后文本，
``structured_content.raw_transcript`` 保留机器转写原文（specs/interview-record.md）。
降级策略：清洗/说话人分离失败时使用原始转写继续（中性标签、warning 留痕）；
LLM 结构化输出非法按任务失败处理，保留重试入口。
"""

from app.prompts.interview import (
    INTERVIEW_CLEANUP_SYSTEM_PROMPT,
    INTERVIEW_STRUCTURE_SYSTEM_PROMPT,
    build_interview_cleanup_user_prompt,
    build_interview_structure_user_prompt,
)
from app.services.ai.llm import LLMService
from app.services.ai.providers import AIProviders
from app.services.ai.speech import SpeechService
from app.services.pipelines.base import (
    GenerationPipeline,
    PipelineContext,
    PipelineError,
    PipelineResult,
)
from app.services.pipelines.common import (
    load_source_bytes,
    parse_datetime,
    parse_llm_json,
    warn,
)
from app.services.storage import get_storage_service


def _brief(exc: Exception) -> str:
    message = getattr(exc, "message", None) or str(exc) or type(exc).__name__
    return message[:200]


def _str_list(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    items = [str(v).strip() for v in value if str(v).strip()]
    return items or None


class InterviewRecordPipeline(GenerationPipeline):
    """询问记录：语音转写 → 转写清洗 → 说话人分离 → LLM 抽取 → 草稿。"""

    record_kind = "interview_record"
    required_capabilities = ("speech", "llm")
    stages = (
        ("speech_transcription", 30),
        ("transcript_cleanup", 50),
        ("speaker_diarization", 60),
        ("llm_extract", 80),
        ("draft", 95),
    )

    def execute_stage(
        self, stage: str, ctx: PipelineContext, providers: AIProviders
    ) -> PipelineResult | None:
        handler = {
            "speech_transcription": self._speech_transcription,
            "transcript_cleanup": self._transcript_cleanup,
            "speaker_diarization": self._speaker_diarization,
            "llm_extract": self._llm_extract,
            "draft": self._draft,
        }[stage]
        return handler(ctx)

    # ---------- 阶段实现 ----------

    def _speech_transcription(self, ctx: PipelineContext) -> None:
        """语音转写为原始 transcript；失败即任务失败（无可辨识语音禁止编造）。"""
        storage = get_storage_service()
        source_file, audio_bytes = load_source_bytes(ctx, storage)
        transcript = SpeechService().transcribe(
            audio_bytes, filename=source_file.original_name or "audio.wav"
        )
        if not transcript:
            raise PipelineError(
                "NO_SPEECH_CONTENT", "音频中未识别到可转写的语音内容，无法生成询问记录"
            )
        ctx.artifacts["raw_transcript"] = transcript

    def _transcript_cleanup(self, ctx: PipelineContext) -> None:
        """LLM 清洗转写文本；失败降级为原始转写（不改变实质含义）。"""
        raw = ctx.artifacts["raw_transcript"]
        try:
            content = LLMService().chat(
                [
                    {"role": "system", "content": INTERVIEW_CLEANUP_SYSTEM_PROMPT},
                    {"role": "user", "content": build_interview_cleanup_user_prompt(raw)},
                ]
            )
            cleaned = parse_llm_json(content, stage="transcript_cleanup").get(
                "cleaned_transcript"
            )
            if not isinstance(cleaned, str) or not cleaned.strip():
                raise ValueError("清洗结果为空")
            ctx.artifacts["clean_transcript"] = cleaned.strip()
        except Exception as exc:
            warn(ctx, f"转写清洗失败，使用机器转写原文继续：{_brief(exc)}")
            ctx.artifacts["clean_transcript"] = raw

    def _speaker_diarization(self, ctx: PipelineContext) -> None:
        """说话人分离：v1 依赖 LLM 在结构化阶段赋予中性标签（询问人/被询问人）。

        本阶段只做标记说明，不调用额外模型；结构化阶段失败时按任务失败处理，
        transcript 已独立落库前的内容保留在任务产物中。
        """
        ctx.artifacts["diarization"] = "deferred_to_llm_neutral_labels"

    def _llm_extract(self, ctx: PipelineContext) -> None:
        """LLM 结构化抽取问答与元数据；解析失败按任务失败处理。"""
        content = LLMService().chat(
            [
                {"role": "system", "content": INTERVIEW_STRUCTURE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_interview_structure_user_prompt(
                        transcript=ctx.artifacts["clean_transcript"],
                        remarks=ctx.remarks,
                    ),
                },
            ]
        )
        ctx.artifacts["draft_json"] = parse_llm_json(content, stage="llm_extract")

    def _draft(self, ctx: PipelineContext) -> PipelineResult:
        """组装落库结构：transcript 与 structured_content 分开保存。"""
        data = ctx.artifacts["draft_json"]
        qa = []
        for raw in data.get("questions_and_answers") or []:
            if not isinstance(raw, dict):
                warn(ctx, "丢弃一条非法问答项（LLM 输出不完整）")
                continue
            question = str(raw.get("question") or "").strip()
            answer = str(raw.get("answer") or "").strip()
            if not question and not answer:
                warn(ctx, "丢弃一条空问答项（LLM 输出不完整）")
                continue
            qa.append({"question": question, "answer": answer})
        fields = {
            "title": str(data.get("title") or "") or None,
            "interviewee_name": str(data.get("interviewee_name") or "") or None,
            "interviewer_names": _str_list(data.get("interviewer_names")),
            "location": str(data.get("location") or "") or None,
            "started_at": parse_datetime(data.get("started_at")),
            "ended_at": parse_datetime(data.get("ended_at")),
            "transcript": ctx.artifacts["clean_transcript"],
            "structured_content": {
                "questions_and_answers": qa,
                # 机器转写原文独立保留，校订后仍可查（契约要求）
                "raw_transcript": ctx.artifacts["raw_transcript"],
            },
            "source_task_id": ctx.task_id,
        }
        return PipelineResult(
            fields=fields, warnings=ctx.artifacts.get("warnings", [])
        )
