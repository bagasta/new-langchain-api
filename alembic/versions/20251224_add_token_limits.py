"""Add token limits and tracking

Revision ID: 20251224_add_token_limits
Revises: 20251223_add_updated_at_api_keys
Create Date: 2024-12-24 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '20251224_add_token_limits'
down_revision = '20251223_add_updated_at_api_keys'
branch_labels = None
depends_on = None


def upgrade():
    # Add token limit columns to agents table
    op.add_column('agents', sa.Column('token_limit', sa.BigInteger(), nullable=True, comment='Maximum tokens allowed for this agent'))
    op.add_column('agents', sa.Column('tokens_used', sa.BigInteger(), nullable=False, server_default='0', comment='Total tokens used by this agent'))
    op.add_column('agents', sa.Column('token_reset_date', sa.DateTime(timezone=True), nullable=True, comment='Optional date for periodic token reset'))
    
    # Add token tracking columns to executions table
    op.add_column('executions', sa.Column('input_tokens', sa.Integer(), nullable=True, comment='Tokens used in input'))
    op.add_column('executions', sa.Column('output_tokens', sa.Integer(), nullable=True, comment='Tokens used in output'))
    op.add_column('executions', sa.Column('total_tokens', sa.Integer(), nullable=True, comment='Total tokens for this execution'))
    
    # Create index for faster queries on token usage
    op.create_index('idx_agents_token_limit', 'agents', ['token_limit', 'tokens_used'])
    op.create_index('idx_executions_tokens', 'executions', ['agent_id', 'total_tokens'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_executions_tokens', table_name='executions')
    op.drop_index('idx_agents_token_limit', table_name='agents')
    
    # Drop columns from executions table
    op.drop_column('executions', 'total_tokens')
    op.drop_column('executions', 'output_tokens')
    op.drop_column('executions', 'input_tokens')
    
    # Drop columns from agents table
    op.drop_column('agents', 'token_reset_date')
    op.drop_column('agents', 'tokens_used')
    op.drop_column('agents', 'token_limit')
