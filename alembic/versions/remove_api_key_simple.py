"""Remove api_key column from users table

Revision ID: remove_api_key_simple
Revises: add_api_key_to_users
Create Date: 2025-10-01 16:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_api_key_simple'
down_revision = '6ee1a8575943'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the unique constraint first
    op.drop_constraint('uq_users_api_key', 'users', type_='unique')

    # Drop the api_key column
    op.drop_column('users', 'api_key')


def downgrade() -> None:
    # Add the api_key column back
    op.add_column('users', sa.Column('api_key', sa.String(length=128), nullable=True))

    # Generate api keys for existing users
    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id FROM users")).fetchall()
    import uuid
    for row in users:
        conn.execute(
            sa.text("UPDATE users SET api_key = :key WHERE id = :id"),
            {"key": uuid.uuid4().hex, "id": row[0]},
        )

    # Make it not null and add unique constraint
    op.alter_column('users', 'api_key', nullable=False)
    op.create_unique_constraint('uq_users_api_key', 'users', ['api_key'])
