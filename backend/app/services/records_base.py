"""三组业务记录共享的 service 基础设施（API.md §4 统一模式）。

共享逻辑：generate 编排（校验上传 → 建草稿 → 建任务 → 提交执行器，单事务）、
数据归属、finalized 防覆盖、审计。
"""

import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppException, conflict, not_found
from app.models.ai_task import AITask
from app.models.user import AuditLog, User
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import AuditLogRepository
from app.services.file_service import FileService
from app.services.storage import StorageService
from app.services.tasks import get_task_executor


class RecordServiceBase:
    # 子类定义：审计动作前缀（inspection_record / photo_report / interview_record）
    audit_entity: str = ""
    # ai_tasks.input_data 中的业务实体种类（worker / 重试守卫据此定位记录）
    record_kind: str = ""

    def __init__(self, session: Session, storage: StorageService | None = None) -> None:
        self.session = session
        self.tasks = TaskRepository(session)
        self.audit = AuditLogRepository(session)
        self.files = FileService(session, storage)
        self.settings = get_settings()

    @staticmethod
    def _is_admin(user: User) -> bool:
        return user.role == "admin"

    def _check_remarks(self, remarks: str | None) -> None:
        max_len = self.settings.REMARKS_MAX_LENGTH
        if remarks is not None and len(remarks) > max_len:
            raise AppException(
                "VALIDATION_ERROR", f"备注长度超过上限（{max_len} 字符）", 400
            )

    def _start_generation(
        self,
        *,
        user: User,
        filename: str | None,
        content_type: str | None,
        data: bytes,
        category: str,
        task_type: str,
        record,
        remarks: str | None,
        request_id: str | None = None,
    ) -> AITask:
        """generate 统一编排（DATABASE.md 事务规则：多表写入单事务）。"""
        self._check_remarks(remarks)
        uploaded = self.files.save_upload(
            filename=filename or "",
            content_type=content_type,
            data=data,
            category=category,
            uploaded_by=user.id,
        )
        self.session.add(record)
        self.session.flush()

        task = AITask(
            task_type=task_type,
            status="pending",
            input_data={
                "record_kind": self.record_kind,
                "record_id": str(record.id),
                "uploaded_file_id": str(uploaded.id),
                "original_name": uploaded.original_name,
                "remarks": remarks,
            },
            created_by=user.id,
        )
        self.tasks.add(task)
        record.source_task_id = task.id
        self.audit.append(
            AuditLog(
                user_id=user.id,
                action=f"{self.audit_entity}.create",
                entity_type=self.audit_entity,
                entity_id=record.id,
                request_id=request_id,
                details={"task_id": str(task.id), "uploaded_file_id": str(uploaded.id)},
            )
        )
        self.session.commit()
        self.session.refresh(task)
        get_task_executor().submit(task.id)
        return task

    def _get_or_404(self, repo, record_id: uuid.UUID, user: User, label: str):
        record = repo.get_scoped(record_id, user.id, self._is_admin(user))
        if record is None:
            raise not_found(f"{label}不存在")
        return record

    @staticmethod
    def _guard_not_finalized(record) -> None:
        """已定稿记录拒绝修改（API.md §4：finalized 不得静默覆盖，返回 409）。"""
        if record.status == "finalized":
            raise conflict("RECORD_FINALIZED", "记录已定稿，不可修改")

    def _audit_finalize(self, user: User, record, request_id: str | None = None) -> None:
        self.audit.append(
            AuditLog(
                user_id=user.id,
                action=f"{self.audit_entity}.finalize",
                entity_type=self.audit_entity,
                entity_id=record.id,
                request_id=request_id,
            )
        )

    def _audit_download(
        self, user: User, record, document_id: uuid.UUID, request_id: str | None = None
    ) -> None:
        self.audit.append(
            AuditLog(
                user_id=user.id,
                action="document.download",
                entity_type=self.audit_entity,
                entity_id=record.id,
                request_id=request_id,
                details={"document_id": str(document_id)},
            )
        )
