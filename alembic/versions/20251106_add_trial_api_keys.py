"""Add trial API keys support

Revision ID: add_trial_api_keys
Revises: add_agent_uploads
Create Date: 2025-11-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_trial_api_keys"
down_revision = "add_agent_uploads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE plan_code_enum ADD VALUE IF NOT EXISTS 'TRIAL'")

    op.add_column(
        "api_keys",
        sa.Column("trial_ip", sa.String(length=45), nullable=True),
    )
    op.create_index(
        "ix_api_keys_trial_ip",
        "api_keys",
        ["trial_ip"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_api_keys_trial_ip", table_name="api_keys")
    op.drop_column("api_keys", "trial_ip")

    # Remove any rows using the trial plan before reverting the ENUM
    op.execute("DELETE FROM api_keys WHERE plan_code = 'TRIAL'")

    op.execute("ALTER TYPE plan_code_enum RENAME TO plan_code_enum_old")
    op.execute("CREATE TYPE plan_code_enum AS ENUM ('PRO_M', 'PRO_Y')")
    op.execute(
        "ALTER TABLE api_keys ALTER COLUMN plan_code TYPE plan_code_enum USING plan_code::text::plan_code_enum"
    )
    op.execute("DROP TYPE plan_code_enum_old")
