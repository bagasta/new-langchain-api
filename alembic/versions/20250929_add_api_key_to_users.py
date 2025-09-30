"""Add api_key column to users

Revision ID: add_api_key_to_users
Revises: cd9e2a65ae6e
Create Date: 2025-09-29
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_api_key_to_users"
down_revision = "cd9e2a65ae6e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("api_key", sa.String(length=128), nullable=True))
    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id FROM users")).fetchall()
    for row in users:
        conn.execute(
            sa.text("UPDATE users SET api_key = :key WHERE id = :id"),
            {"key": uuid.uuid4().hex, "id": row[0]},
        )
    op.alter_column("users", "api_key", nullable=False)
    op.create_unique_constraint("uq_users_api_key", "users", ["api_key"])


def downgrade() -> None:
    op.drop_constraint("uq_users_api_key", "users", type_="unique")
    op.drop_column("users", "api_key")
