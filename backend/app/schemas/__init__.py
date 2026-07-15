"""Pydantic schemas for the Fire Intelligence Platform API.

All request and response models are defined in domain-specific modules
and re-exported here for convenient imports.
"""

from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
)
from app.schemas.inspection import (
    GenerateResponse,
    InspectionRecordItemSchema,
    InspectionRecordResponse,
    InspectionRecordUpdate,
)
from app.schemas.interview import (
    InterviewRecordResponse,
    InterviewRecordUpdate,
)
from app.schemas.knowledge import (
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
)
from app.schemas.photo_report import (
    PhotoReportImageSchema,
    PhotoReportImageUpdate,
    PhotoReportResponse,
    PhotoReportUpdate,
)
from app.schemas.qa import (
    QAQueryRequest,
    QAResponse,
    QASource,
)
from app.schemas.statistics import StatisticsResponse
from app.schemas.task import TaskResponse

__all__ = [
    # common
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "PaginatedResponse",
    # auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    # inspection
    "GenerateResponse",
    "InspectionRecordItemSchema",
    "InspectionRecordResponse",
    "InspectionRecordUpdate",
    # photo report
    "PhotoReportImageSchema",
    "PhotoReportImageUpdate",
    "PhotoReportResponse",
    "PhotoReportUpdate",
    # interview
    "InterviewRecordResponse",
    "InterviewRecordUpdate",
    # knowledge
    "KnowledgeDocumentResponse",
    "KnowledgeDocumentListResponse",
    # task
    "TaskResponse",
    # statistics
    "StatisticsResponse",
    # qa
    "QAQueryRequest",
    "QASource",
    "QAResponse",
]
