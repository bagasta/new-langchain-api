"""Add agent uploads table and track upload provenance on embeddings

Revision ID: add_agent_uploads
Revises: add_api_key_to_users
Create Date: 2025-10-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    for column in inspector.get_columns(table_name):
        if column.get("name") == column_name:
            return True
    return False

# revision identifiers, used by Alembic.
revision = "add_agent_uploads"
down_revision = "add_mcp_fields_to_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "agent_uploads"):
        op.create_table(
            "agent_uploads",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("filename", sa.String(length=512), nullable=False),
            sa.Column("content_type", sa.String(length=255), nullable=True),
            sa.Column("size_bytes", sa.BigInteger(), nullable=True),
            sa.Column("chunk_count", sa.Integer(), nullable=False),
            sa.Column(
                "embedding_ids",
                postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                nullable=False,
                server_default=sa.text("'{}'::uuid[]"),
            ),
            sa.Column(
                "details",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["agent_id"],
                ["agents.id"],
                ondelete="CASCADE",
                name="fk_agent_uploads_agent_id_agents",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="SET NULL",
                name="fk_agent_uploads_user_id_users",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_agent_uploads_agent_id"),
            "agent_uploads",
            ["agent_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_agent_uploads_user_id"),
            "agent_uploads",
            ["user_id"],
            unique=False,
        )

    if not _column_exists(bind, "embeddings", "upload_id"):
        op.add_column(
            "embeddings",
            sa.Column(
                "upload_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_index(
            op.f("ix_embeddings_upload_id"),
            "embeddings",
            ["upload_id"],
            unique=False,
        )
        op.create_foreign_key(
            "fk_embeddings_upload_id_agent_uploads",
            "embeddings",
            "agent_uploads",
            ["upload_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _column_exists(bind, "embeddings", "upload_id"):
        op.drop_constraint(
            "fk_embeddings_upload_id_agent_uploads",
            "embeddings",
            type_="foreignkey",
        )
        op.drop_index(op.f("ix_embeddings_upload_id"), table_name="embeddings")
        op.drop_column("embeddings", "upload_id")

    if _table_exists(bind, "agent_uploads"):
        op.drop_index(op.f("ix_agent_uploads_user_id"), table_name="agent_uploads")
        op.drop_index(op.f("ix_agent_uploads_agent_id"), table_name="agent_uploads")
        op.drop_table("agent_uploads")
