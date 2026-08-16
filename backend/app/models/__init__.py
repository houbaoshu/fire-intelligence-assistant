"""Database models. Import all models so they register on Base.metadata."""
from .base import Base
from .user import User, UserProfile
from .inspection import InspectionRecord, InspectionRecordItem
from .photo_report import PhotoReport, PhotoReportImage
from .interview import InterviewRecord
from .file import UploadedFile
from .document import GeneratedDocument
from .task import AiTask
from .knowledge import KnowledgeDocument, KnowledgeIndexJob
from .audit import AuditLog
from .org import Organization, Department
from .permission import Permission, RolePermission
from .aiplatform import PromptVersion, ModelConfiguration, EvaluationResult, PluginRecord

__all__ = [
    "Base",
    "User",
    "UserProfile",
    "InspectionRecord",
    "InspectionRecordItem",
    "PhotoReport",
    "PhotoReportImage",
    "InterviewRecord",
    "UploadedFile",
    "GeneratedDocument",
    "AiTask",
    "KnowledgeDocument",
    "KnowledgeIndexJob",
    "AuditLog",
    "Organization",
    "Department",
    "Permission",
    "RolePermission",
    "PromptVersion",
    "ModelConfiguration",
    "EvaluationResult",
    "PluginRecord",
]
