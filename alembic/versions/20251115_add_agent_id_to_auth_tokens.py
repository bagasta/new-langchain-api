"""Add agent_id to auth_tokens for per-agent auth

Revision ID: add_agent_id_to_auth_tokens
Revises: add_trial_api_keys
Create Date: 2025-11-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_agent_id_to_auth_tokens"
down_revision = "add_trial_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_tokens",
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_auth_tokens_agent_id"),
        "auth_tokens",
        ["agent_id"],
        unique=False,
    )
    op.create_foreign_key(
        "auth_tokens_agent_id_fkey",
        "auth_tokens",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("auth_tokens_agent_id_fkey", "auth_tokens", type_="foreignkey")
    op.drop_index(op.f("ix_auth_tokens_agent_id"), table_name="auth_tokens")
    op.drop_column("auth_tokens", "agent_id")
