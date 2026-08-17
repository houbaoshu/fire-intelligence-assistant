"""三组业务记录的生成管线定义（阶段序列见 ARCHITECTURE.md §11/§12/§13）。"""

from app.services.pipelines.base import GenerationPipeline


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


# task_type → 管线实例（worker 据此分发；M3+ 在此注册知识库等任务类型）
PIPELINES: dict[str, GenerationPipeline] = {
    "inspection_record_generation": InspectionRecordPipeline(),
    "photo_report_generation": PhotoReportPipeline(),
    "interview_record_generation": InterviewRecordPipeline(),
}
