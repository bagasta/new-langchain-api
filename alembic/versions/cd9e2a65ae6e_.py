"""Initial schema

Revision ID: cd9e2a65ae6e
Revises:
Create Date: 2025-09-26 22:32:12.442490

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision = "cd9e2a65ae6e"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    if not _has_table(bind, "tools"):
        op.create_table(
            "tools",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("type", sa.Enum("BUILTIN", "CUSTOM", name="tooltype"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_tools_name"), "tools", ["name"], unique=True)

    if not _has_table(bind, "agents"):
        op.create_table(
            "agents",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("status", sa.Enum("ACTIVE", "INACTIVE", "DELETED", name="agentstatus"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_agents_user_id"), "agents", ["user_id"], unique=False)

    if not _has_table(bind, "agent_tools"):
        op.create_table(
            "agent_tools",
            sa.Column("agent_id", sa.UUID(), nullable=False),
            sa.Column("tool_id", sa.UUID(), nullable=False),
            sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("agent_id", "tool_id", "id"),
        )
        op.create_index(op.f("ix_agent_tools_id"), "agent_tools", ["id"], unique=False)

    if not _has_table(bind, "auth_tokens"):
        op.create_table(
            "auth_tokens",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("service", sa.String(length=50), nullable=False),
            sa.Column("access_token", sa.String(), nullable=False),
            sa.Column("refresh_token", sa.String(), nullable=True),
            sa.Column("scope", sa.ARRAY(sa.String()), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_auth_tokens_user_id"), "auth_tokens", ["user_id"], unique=False)

    if not _has_table(bind, "embeddings"):
        op.create_table(
            "embeddings",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("agent_id", sa.UUID(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=False),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_embeddings_agent_id"), "embeddings", ["agent_id"], unique=False)

    if not _has_table(bind, "executions"):
        op.create_table(
            "executions",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("agent_id", sa.UUID(), nullable=False),
            sa.Column("input", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("status", sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", name="executionstatus"), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_executions_agent_id"), "executions", ["agent_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_tools_name"), table_name="tools")
    op.drop_table("tools")
    op.drop_index(op.f("ix_executions_agent_id"), table_name="executions")
    op.drop_table("executions")
    op.drop_index(op.f("ix_embeddings_agent_id"), table_name="embeddings")
    op.drop_table("embeddings")
    op.drop_index(op.f("ix_auth_tokens_user_id"), table_name="auth_tokens")
    op.drop_table("auth_tokens")
    op.drop_index(op.f("ix_agents_user_id"), table_name="agents")
    op.drop_table("agents")
    op.drop_index(op.f("ix_agent_tools_id"), table_name="agent_tools")
    op.drop_table("agent_tools")
