"""Fix api_keys is_active column type

Revision ID: fix_api_keys_is_active
Revises: remove_api_key_simple
Create Date: 2025-10-01 17:12:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_api_keys_is_active'
down_revision = 'remove_api_key_simple'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix the is_active column type from String to Boolean
    # First update existing data to convert string 'true' to boolean true
    op.execute("UPDATE api_keys SET is_active = true WHERE is_active = 'true'")
    op.execute("UPDATE api_keys SET is_active = false WHERE is_active = 'false'")

    # Then alter the column type
    op.alter_column('api_keys', 'is_active',
                    existing_type=sa.String(),
                    type_=sa.Boolean(),
                    existing_default=True,
                    existing_nullable=False,
                    postgresql_using='is_active::boolean')


def downgrade() -> None:
    # Revert back to String type
    op.alter_column('api_keys', 'is_active',
                    existing_type=sa.Boolean(),
                    type_=sa.String(),
                    existing_default=True,
                    existing_nullable=False)