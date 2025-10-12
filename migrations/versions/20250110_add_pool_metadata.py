"""add pool_metadata table and pool_type column

Revision ID: 20250110_add_pool_metadata
Revises: 338f8c141964
Create Date: 2025-01-10 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250110_add_pool_metadata'
down_revision = '338f8c141964'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pool_metadata',
        sa.Column('pool_address', sa.Text(), primary_key=True),
        sa.Column('owner_program', sa.Text(), nullable=False),
        sa.Column('pool_type', sa.String(length=50), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_pool_metadata_owner_program', 'pool_metadata', ['owner_program'])
    op.create_index('ix_pool_metadata_pool_type', 'pool_metadata', ['pool_type'])
    op.create_index('ix_pool_metadata_fetched_at', 'pool_metadata', ['fetched_at'])

    op.add_column('latest_token_scores', sa.Column('pool_type', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('latest_token_scores', 'pool_type')
    op.drop_index('ix_pool_metadata_fetched_at', table_name='pool_metadata')
    op.drop_index('ix_pool_metadata_pool_type', table_name='pool_metadata')
    op.drop_index('ix_pool_metadata_owner_program', table_name='pool_metadata')
    op.drop_table('pool_metadata')
