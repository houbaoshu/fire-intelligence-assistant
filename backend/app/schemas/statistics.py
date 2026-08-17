"""Statistics schema（API.md §7）。"""

from datetime import datetime

from pydantic import BaseModel


class StatusCount(BaseModel):
    total: int
    by_status: dict[str, int]


class RecordsStats(BaseModel):
    inspection_records: StatusCount
    photo_reports: StatusCount
    interview_records: StatusCount


class KnowledgeStats(BaseModel):
    """知识库聚合计数（API.md §7 knowledge 段）。"""

    document_count: int = 0
    indexed_count: int = 0
    indexing_count: int = 0
    failed_count: int = 0


class GeneratedDocumentsStats(BaseModel):
    total: int


class StatisticsResponse(BaseModel):
    scope: str
    generated_at: datetime
    records: RecordsStats
    tasks: StatusCount
    knowledge: KnowledgeStats
    generated_documents: GeneratedDocumentsStats
