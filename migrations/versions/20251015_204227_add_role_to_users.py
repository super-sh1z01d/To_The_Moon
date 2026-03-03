"""add role to users

Revision ID: add_role_to_users
Revises: 20251015_oauth
Create Date: 2025-10-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_role_to_users'
down_revision = '20251015_oauth'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "role" not in cols:
        op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='user'))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "role" in cols:
        op.drop_column('users', 'role')
