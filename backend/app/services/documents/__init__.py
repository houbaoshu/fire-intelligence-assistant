"""文档生成子系统（ARCHITECTURE.md §14）。

数据库记录 → 模板数据映射 → docxtpl 渲染 → DOCX → 对象存储 generated/ →
generated_documents 元数据入库（version 递增，不覆盖历史版本）。
"""

from app.services.documents.service import (
    DOCX_MEDIA_TYPE,
    DocumentGenerationService,
)

__all__ = ["DOCX_MEDIA_TYPE", "DocumentGenerationService"]
