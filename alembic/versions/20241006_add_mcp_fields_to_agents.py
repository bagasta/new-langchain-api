"""Add MCP fields to agents

Revision ID: add_mcp_fields_to_agents
Revises: fix_api_keys_is_active
Create Date: 2024-10-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_mcp_fields_to_agents"
down_revision = "fix_api_keys_is_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "mcp_servers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "allowed_tools",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )


def downgrade() -> None:
    op.drop_column("agents", "allowed_tools")
    op.drop_column("agents", "mcp_servers")
