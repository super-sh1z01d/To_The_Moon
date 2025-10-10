"""migrate to postgresql with optimizations

Revision ID: 338f8c141964
Revises: 0003_add_hybrid_momentum_scoring
Create Date: 2025-10-10 10:37:51.850540

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '338f8c141964'
down_revision = '0003_add_hybrid_momentum_scoring'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to tokens table for extracted metrics
    op.add_column('tokens', sa.Column('liquidity_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('tokens', sa.Column('primary_dex', sa.String(length=50), nullable=True))
    
    # Add indexes for performance
    op.create_index('idx_tokens_liquidity', 'tokens', ['liquidity_usd'], unique=False)
    op.create_index('idx_tokens_primary_dex', 'tokens', ['primary_dex'], unique=False)
    op.create_index('idx_token_scores_smoothed', 'token_scores', ['smoothed_score'], unique=False)
    op.create_index('idx_token_scores_token_created', 'token_scores', ['token_id', 'created_at'], unique=False)
    
    # For PostgreSQL: Convert JSON to JSONB (will be no-op for SQLite)
    # This is handled by the model definition with .with_variant()


def downgrade() -> None:
    # Remove indexes
    op.drop_index('idx_token_scores_token_created', table_name='token_scores')
    op.drop_index('idx_token_scores_smoothed', table_name='token_scores')
    op.drop_index('idx_tokens_primary_dex', table_name='tokens')
    op.drop_index('idx_tokens_liquidity', table_name='tokens')
    
    # Remove columns
    op.drop_column('tokens', 'primary_dex')
    op.drop_column('tokens', 'liquidity_usd')
