"""add hybrid momentum scoring support

Revision ID: 0003_add_hybrid_momentum_scoring
Revises: 0002_add_smoothed_score
Create Date: 2025-09-17 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_add_hybrid_momentum_scoring"
down_revision = "0002_add_smoothed_score"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to token_scores table for hybrid momentum model
    op.add_column('token_scores', sa.Column('raw_components', sa.JSON(), nullable=True))
    op.add_column('token_scores', sa.Column('smoothed_components', sa.JSON(), nullable=True))
    op.add_column('token_scores', sa.Column('scoring_model', sa.String(50), nullable=False, server_default='hybrid_momentum'))
    
    # Add new settings for hybrid momentum model
    op.execute("""
        INSERT INTO app_settings (key, value) VALUES
        ('scoring_model_active', 'hybrid_momentum'),
        ('w_tx', '0.25'),
        ('w_vol', '0.25'),
        ('w_fresh', '0.25'),
        ('w_oi', '0.25'),
        ('ewma_alpha', '0.3'),
        ('freshness_threshold_hours', '6.0')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    # Remove new columns from token_scores table
    op.drop_column('token_scores', 'scoring_model')
    op.drop_column('token_scores', 'smoothed_components')
    op.drop_column('token_scores', 'raw_components')
    
    # Remove hybrid momentum settings
    op.execute("""
        DELETE FROM app_settings WHERE key IN (
            'scoring_model_active',
            'w_tx',
            'w_vol', 
            'w_fresh',
            'w_oi',
            'ewma_alpha',
            'freshness_threshold_hours'
        )
    """)