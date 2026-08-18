"""m8 ai platform: prompt_versions model_configurations evaluation_results plugins

Revision ID: c2e7f4a91b63
Revises: a1b508a2c765
Create Date: 2026-08-17 23:40:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c2e7f4a91b63'
down_revision: str | Sequence[str] | None = 'a1b508a2c765'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('evaluation_results',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('total_questions', sa.Integer(), nullable=False),
    sa.Column('passed', sa.Integer(), nullable=False),
    sa.Column('details', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('completed', 'failed')", name='ck_evaluation_results_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('model_configurations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('provider', sa.String(), nullable=False),
    sa.Column('model_name', sa.String(), nullable=False),
    sa.Column('base_url', sa.String(), nullable=True),
    sa.Column('api_key_ref', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("kind IN ('llm', 'vision', 'ocr', 'speech', 'embedding', 'reranker')", name='ck_model_configurations_kind'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_model_configurations_kind_active', 'model_configurations', ['kind', 'is_active'], unique=False)
    op.create_table('plugins',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('version', sa.String(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('entry_point', sa.String(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_plugins_name', 'plugins', ['name'], unique=True)
    op.create_table('prompt_versions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('key', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key', 'version', name='uq_prompt_versions_key_version')
    )
    op.create_index('ix_prompt_versions_key', 'prompt_versions', ['key'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_prompt_versions_key', table_name='prompt_versions')
    op.drop_table('prompt_versions')
    op.drop_index('ix_plugins_name', table_name='plugins')
    op.drop_table('plugins')
    op.drop_index('ix_model_configurations_kind_active', table_name='model_configurations')
    op.drop_table('model_configurations')
    op.drop_table('evaluation_results')
