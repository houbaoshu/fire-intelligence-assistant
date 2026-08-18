"""三组业务记录共享的 service 基础设施（API.md §4 统一模式）。

共享逻辑：generate 编排（校验上传 → 建草稿 → 建任务 → 提交执行器，单事务）、
数据归属、finalized 防覆盖、审计。

数据归属（M6）：admin 可见全部；supervisor 可见所属组织成员创建的记录
（未分配组织时回退为本人记录）；inspector / viewer 仅本人记录。
更新权限（M6）：编辑本人记录需 record.create；修改他人记录需 record.review；
将记录推进为 finalized 需 record.finalize（specs/_common.md「角色与权限」）。
"""

import uuid

from sqlalchemy.orm import Session

from app.core.cache import invalidate_read_models
from app.core.config import get_settings
from app.core.exceptions import AppException, conflict, forbidden, not_found
from app.models.ai_task import AITask
from app.models.user import AuditLog, User
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import AuditLogRepository, UserRepository
from app.services.file_service import FileService
from app.services.idempotency import compute_request_hash, find_idempotent_task
from app.services.permission_service import PermissionService
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

    def _visible_creator_ids(self, user: User) -> list[uuid.UUID] | None:
        """记录可见范围的创建者集合：None=不过滤（admin）；supervisor 有组织=
        组织全体成员；其余（含未分配组织的 supervisor）= 仅本人。"""
        if self._is_admin(user):
            return None
        if user.role == "supervisor" and user.organization_id is not None:
            return UserRepository(self.session).ids_in_organization(user.organization_id)
        return [user.id]

    def _require_permission(self, user: User, code: str) -> None:
        if not PermissionService(self.session).has_permission(user.role, code):
            raise forbidden("当前角色无权执行此操作")

    def _check_update_permission(
        self, user: User, record, new_status: str | None
    ) -> None:
        """更新授权：编辑本人记录需 record.create；修改他人记录需 record.review；
        推进 finalized 需 record.finalize。"""
        if record.created_by == user.id:
            self._require_permission(user, "record.create")
        else:
            self._require_permission(user, "record.review")
        if new_status == "finalized" and record.status != "finalized":
            self._require_permission(user, "record.finalize")

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
        idempotency_key: str | None = None,
    ) -> AITask:
        """generate 统一编排（DATABASE.md 事务规则：多表写入单事务）。

        幂等提交（API.md §1.5）：带 Idempotency-Key 的重复提交直接返回
        首个任务，不重复创建上传/草稿/任务；同 key 不同请求体返回 409。
        """
        request_hash = compute_request_hash(data, remarks)
        existing = find_idempotent_task(
            self.session,
            user_id=user.id,
            task_type=task_type,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing is not None:
            return existing
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
            max_attempts=self.settings.TASK_MAX_ATTEMPTS,
            idempotency_key=idempotency_key,
            request_hash=request_hash if idempotency_key else None,
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
        invalidate_read_models()  # 新记录/任务：失效 statistics 缓存（M7）
        get_task_executor().submit(task.id)
        return task

    def _get_or_404(self, repo, record_id: uuid.UUID, user: User, label: str):
        record = repo.get_scoped(record_id, self._visible_creator_ids(user))
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
