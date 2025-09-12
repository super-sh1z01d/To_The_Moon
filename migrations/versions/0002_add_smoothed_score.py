"""add smoothed_score field

Revision ID: 0002_add_smoothed_score
Revises: 0001_init
Create Date: 2025-09-12 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_add_smoothed_score"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add smoothed_score column to token_scores table
    op.add_column('token_scores', sa.Column('smoothed_score', sa.Numeric(10, 4), nullable=True))


def downgrade() -> None:
    # Remove smoothed_score column from token_scores table
    op.drop_column('token_scores', 'smoothed_score')
