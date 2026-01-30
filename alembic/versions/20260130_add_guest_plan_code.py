"""Add GUEST plan code

Revision ID: add_guest_plan_code
Revises: add_trial_api_keys
Create Date: 2026-01-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260130_add_guest_plan_code"
down_revision = "20251224_add_token_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add GUEST to plan_code_enum"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if not inspector.has_table("api_keys"):
        return
    
    # Add GUEST value to the existing enum
    op.execute("ALTER TYPE plan_code_enum ADD VALUE IF NOT EXISTS 'GUEST'")


def downgrade() -> None:
    """Remove GUEST from plan_code_enum"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if not inspector.has_table("api_keys"):
        return
    
    # Remove any rows using the GUEST plan before reverting the ENUM
    op.execute("DELETE FROM api_keys WHERE plan_code = 'GUEST'")
    
    # Note: PostgreSQL doesn't support removing enum values directly
    # You would need to recreate the enum type without GUEST
    # For simplicity, we'll just delete the data using GUEST
    # If you need to fully remove GUEST, you'd need to:
    # 1. Create new enum without GUEST
    # 2. Alter column to use new enum
    # 3. Drop old enum
