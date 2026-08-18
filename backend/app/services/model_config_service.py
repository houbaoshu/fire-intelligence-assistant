"""模型配置管理（M8，API.md §12.2）：model_configurations 的 CRUD。

安全约束：api_key_ref 只存密钥环境变量名，密钥本身绝不落库；
运行时解析见 app/services/ai/providers.py（模型路由）。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.models.ai_platform import ModelConfiguration
from app.schemas.ai_platform import ModelConfigCreateRequest, ModelConfigUpdateRequest


class ModelConfigService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[ModelConfiguration]:
        stmt = select(ModelConfiguration).order_by(
            ModelConfiguration.kind, ModelConfiguration.priority, ModelConfiguration.created_at
        )
        return list(self.session.execute(stmt).scalars().all())

    def create(self, payload: ModelConfigCreateRequest) -> ModelConfiguration:
        row = ModelConfiguration(**payload.model_dump())
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def update(
        self, config_id: uuid.UUID, payload: ModelConfigUpdateRequest
    ) -> ModelConfiguration:
        row = self.session.get(ModelConfiguration, config_id)
        if row is None:
            raise not_found("模型配置不存在")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        self.session.commit()
        self.session.refresh(row)
        return row

    def delete(self, config_id: uuid.UUID) -> ModelConfiguration:
        """硬删除（API.md §12.2）：配置为纯管理数据，删除即解除路由引用。"""
        row = self.session.get(ModelConfiguration, config_id)
        if row is None:
            raise not_found("模型配置不存在")
        self.session.delete(row)
        self.session.commit()
        return row
