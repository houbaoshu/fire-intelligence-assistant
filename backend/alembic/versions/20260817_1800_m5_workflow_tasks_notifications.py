"""m5 workflow: ai_tasks execution tracking + notifications

Revision ID: f5a1c3e7b942
Revises: 0b026e5b4905
Create Date: 2026-08-17 18:00:00.000000

ai_tasks 新增执行追踪与幂等列（attempt_count / max_attempts / worker_id /
lease_expires_at / queued_at / idempotency_key / request_hash），
新增 notifications 正式表。列定义以 docs/DATABASE.md 为准。
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'f5a1c3e7b942'
down_revision: str | Sequence[str] | None = '0b026e5b4905'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('ai_tasks', sa.Column('queued_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ai_tasks', sa.Column('attempt_count', sa.Integer(), server_default='1', nullable=False))
    op.add_column('ai_tasks', sa.Column('max_attempts', sa.Integer(), server_default='3', nullable=False))
    op.add_column('ai_tasks', sa.Column('worker_id', sa.String(), nullable=True))
    op.add_column('ai_tasks', sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ai_tasks', sa.Column('idempotency_key', sa.String(), nullable=True))
    op.add_column('ai_tasks', sa.Column('request_hash', sa.String(), nullable=True))
    with op.batch_alter_table('ai_tasks') as batch_op:
        batch_op.create_check_constraint('ck_ai_tasks_attempt_count', 'attempt_count >= 1')
    op.create_index('ix_ai_tasks_lease_expires_at', 'ai_tasks', ['lease_expires_at'], unique=False)
    op.create_index('ux_ai_tasks_idempotency', 'ai_tasks', ['created_by', 'task_type', 'idempotency_key'], unique=True)
    op.create_table('notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('entity_type', sa.String(), nullable=True),
    sa.Column('entity_id', sa.Uuid(), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("type IN ('task_completed', 'task_failed', 'task_cancelled')", name='ck_notifications_type'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_user_created_at', 'notifications', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_notifications_user_read_at', 'notifications', ['user_id', 'read_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_notifications_user_read_at', table_name='notifications')
    op.drop_index('ix_notifications_user_created_at', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ux_ai_tasks_idempotency', table_name='ai_tasks')
    op.drop_index('ix_ai_tasks_lease_expires_at', table_name='ai_tasks')
    with op.batch_alter_table('ai_tasks') as batch_op:
        batch_op.drop_constraint('ck_ai_tasks_attempt_count', type_='check')
    op.drop_column('ai_tasks', 'request_hash')
    op.drop_column('ai_tasks', 'idempotency_key')
    op.drop_column('ai_tasks', 'lease_expires_at')
    op.drop_column('ai_tasks', 'worker_id')
    op.drop_column('ai_tasks', 'max_attempts')
    op.drop_column('ai_tasks', 'attempt_count')
    op.drop_column('ai_tasks', 'queued_at')
