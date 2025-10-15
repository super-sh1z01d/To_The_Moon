"""add role to users

Revision ID: add_role_to_users
Revises: 
Create Date: 2025-10-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_role_to_users'
down_revision = None  # Update this with the actual previous revision ID if needed
branch_labels = None
depends_on = None


def upgrade():
    # Add role column with default 'user'
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='user'))


def downgrade():
    op.drop_column('users', 'role')
