"""Approved enum values (single source of truth for code-level checks).

Database-level enum definitions live in DATABASE.md; this module mirrors them
for validation and display purposes only.
"""
from __future__ import annotations

# users.role
USER_ROLES = ("admin", "supervisor", "inspector", "viewer")

# inspection_records / photo_reports / interview_records .status
RECORD_STATUSES = (
    "draft",
    "processing",
    "generated",
    "reviewed",
    "finalized",
    "archived",
    "failed",
)

# inspection_record_items.item_type
ITEM_TYPES = ("compliant", "violation", "hazard", "observation", "recommendation")

# inspection_record_items.severity
SEVERITIES = ("low", "medium", "high", "critical")

# uploaded_files.category
FILE_CATEGORIES = (
    "video",
    "image",
    "audio",
    "document",
    "template",
    "generated_document",
    "knowledge_source",
)

# generated_documents.document_type
DOCUMENT_TYPES = (
    "inspection_record_docx",
    "photo_report_docx",
    "interview_record_docx",
    "inspection_record_pdf",
    "photo_report_pdf",
    "interview_record_pdf",
)

# ai_tasks.status
TASK_STATUSES = ("pending", "queued", "processing", "completed", "failed", "cancelled")

# ai_tasks.task_type
TASK_TYPES = (
    "inspection_record_generation",
    "photo_report_generation",
    "interview_record_generation",
    "speech_transcription",
    "video_analysis",
    "document_generation",
    "knowledge_indexing",
    "knowledge_reindexing",
)

# knowledge_documents.status
KNOWLEDGE_STATUSES = ("uploaded", "parsing", "indexing", "indexed", "failed", "outdated")

# knowledge_index_jobs.action
INDEX_ACTIONS = ("index", "reindex", "delete_index", "full_rebuild")
