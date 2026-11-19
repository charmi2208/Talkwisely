"""Manual action items, task completion time and knowledge-base categories

- action_items.conversation_id becomes nullable (tasks people add by hand)
- action_items.created_by and action_items.completed_at are added
- knowledge_documents.category is added and backfilled from the first chunk's
  metadata, where the category used to live

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19 16:34:49.989316
"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_NAME = "fk_action_items_created_by_users"


def upgrade() -> None:
    with op.batch_alter_table("action_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("created_by", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
        batch_op.alter_column("conversation_id", existing_type=sa.VARCHAR(length=36), nullable=True)
        batch_op.create_foreign_key(FK_NAME, "users", ["created_by"], ["id"])

    with op.batch_alter_table("knowledge_documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(length=100), server_default="general", nullable=False))

    # Backfill categories from chunk metadata (needs a live connection; skipped when
    # generating SQL with --sql, where rows can't be read)
    if op.get_context().as_sql:
        return
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT document_id, extra_metadata FROM knowledge_chunks WHERE chunk_index = 0"
    )).fetchall()
    for document_id, metadata in rows:
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except ValueError:
                metadata = None
        category = (metadata or {}).get("category") if isinstance(metadata, dict) else None
        if category:
            bind.execute(
                sa.text("UPDATE knowledge_documents SET category = :category WHERE id = :id"),
                {"category": str(category)[:100], "id": document_id},
            )


def downgrade() -> None:
    with op.batch_alter_table("knowledge_documents", schema=None) as batch_op:
        batch_op.drop_column("category")

    # Hand-added tasks have no conversation and can't satisfy NOT NULL again
    op.execute("DELETE FROM action_items WHERE conversation_id IS NULL")
    with op.batch_alter_table("action_items", schema=None) as batch_op:
        batch_op.drop_constraint(FK_NAME, type_="foreignkey")
        batch_op.alter_column("conversation_id", existing_type=sa.VARCHAR(length=36), nullable=False)
        batch_op.drop_column("completed_at")
        batch_op.drop_column("created_by")
