"""Add updated_at column to api_keys if missing

Revision ID: add_updated_at_api_keys
Revises: add_agent_id_to_auth_tokens
Create Date: 2025-12-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251223_add_updated_at_api_keys"
down_revision = "add_agent_id_to_auth_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("api_keys"):
        return

    columns = {col["name"] for col in inspector.get_columns("api_keys")}
    if "updated_at" not in columns:
        op.add_column("api_keys", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("api_keys"):
        return

    columns = {col["name"] for col in inspector.get_columns("api_keys")}
    if "updated_at" in columns:
        op.drop_column("api_keys", "updated_at")
