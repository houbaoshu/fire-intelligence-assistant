"""uploaded_files / generated_documents 数据访问。"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.generated_document import GeneratedDocument
from app.models.uploaded_file import UploadedFile


class UploadedFileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, file_id: uuid.UUID) -> UploadedFile | None:
        stmt = select(UploadedFile).where(
            UploadedFile.id == file_id, UploadedFile.deleted_at.is_(None)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def add(self, file: UploadedFile) -> UploadedFile:
        self.session.add(file)
        self.session.flush()
        return file


class GeneratedDocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def latest_for_entity(
        self, source_entity_type: str, source_entity_id: uuid.UUID
    ) -> GeneratedDocument | None:
        stmt = (
            select(GeneratedDocument)
            .where(
                GeneratedDocument.source_entity_type == source_entity_type,
                GeneratedDocument.source_entity_id == source_entity_id,
            )
            .order_by(GeneratedDocument.version.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def next_version(self, source_entity_type: str, source_entity_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(GeneratedDocument.version), 0)).where(
            GeneratedDocument.source_entity_type == source_entity_type,
            GeneratedDocument.source_entity_id == source_entity_id,
        )
        return self.session.execute(stmt).scalar_one() + 1

    def add(self, document: GeneratedDocument) -> GeneratedDocument:
        self.session.add(document)
        self.session.flush()
        return document
