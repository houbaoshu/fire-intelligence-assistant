"""Document generation task handler.

Renders a Word document from saved structured business data (versioned).
"""
from __future__ import annotations

import uuid

from app.services.document_service import DocumentService
from app.services.tasks.registry import TaskContext, register_handler


@register_handler("document_generation")
def handle_document_generation(ctx: TaskContext) -> None:
    entity_type = ctx.input_data.get("entity_type")
    entity_id = uuid.UUID(ctx.input_data["entity_id"])

    ctx.set_progress(20, "collecting_data")
    svc = DocumentService(ctx.db)
    ctx.set_progress(50, "rendering")
    generated = svc.generate_document(
        _current_user(ctx), entity_type, entity_id
    )
    ctx.set_progress(100, None)
    ctx.set_result(
        {
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "document_id": str(generated.id),
            "version": generated.version,
        }
    )


def _current_user(ctx: TaskContext):
    from app.models.user import User

    user = ctx.db.get(User, ctx.user_id)
    if user is None:
        raise RuntimeError("任务创建者不存在")
    return user
