"""
Re-export every SQLAlchemy model so Alembic's ``target_metadata``
can discover them through a single import.

Usage::

    from app.models import User, InspectionRecord, AITask  # etc.
"""

from app.models.audit import AuditLog
from app.models.document import GeneratedDocument
from app.models.file import UploadedFile
from app.models.inspection import InspectionRecord, InspectionRecordItem
from app.models.interview import InterviewRecord
from app.models.knowledge import KnowledgeDocument, KnowledgeIndexJob
from app.models.model_config import ModelConfiguration
from app.models.organization import Department, Organization, UserRole
from app.models.photo_report import PhotoReport, PhotoReportImage
from app.models.prompt import PromptVersion
from app.models.task import AITask
from app.models.user import User
from app.models.user_profile import UserProfile

__all__ = [
    "AuditLog",
    "GeneratedDocument",
    "UploadedFile",
    "InspectionRecord",
    "InspectionRecordItem",
    "InterviewRecord",
    "KnowledgeDocument",
    "KnowledgeIndexJob",
    "ModelConfiguration",
    "Organization",
    "Department",
    "UserRole",
    "PhotoReport",
    "PhotoReportImage",
    "PromptVersion",
    "AITask",
    "User",
    "UserProfile",
]
