"""三组业务记录的生成管线注册表（阶段序列见 ARCHITECTURE.md §11/§12/§13）。

管线实现见同包 inspection.py / photo.py / interview.py；worker 按 task_type
在此分发。
"""

from app.services.pipelines.base import GenerationPipeline
from app.services.pipelines.inspection import InspectionRecordPipeline
from app.services.pipelines.interview import InterviewRecordPipeline
from app.services.pipelines.photo import PhotoReportPipeline

__all__ = [
    "InspectionRecordPipeline",
    "InterviewRecordPipeline",
    "PhotoReportPipeline",
    "PIPELINES",
]

# task_type → 管线实例（worker 据此分发；M3+ 在此注册知识库等任务类型）
PIPELINES: dict[str, GenerationPipeline] = {
    "inspection_record_generation": InspectionRecordPipeline(),
    "photo_report_generation": PhotoReportPipeline(),
    "interview_record_generation": InterviewRecordPipeline(),
}
