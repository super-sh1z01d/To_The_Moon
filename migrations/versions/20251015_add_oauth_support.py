"""Add OAuth support to User model

Revision ID: 20251015_oauth
Revises: ab9ca7c0df3d
Create Date: 2025-10-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251015_oauth'
down_revision = 'ab9ca7c0df3d'
branch_labels = None
depends_on = None


def upgrade():
    # Make hashed_password nullable for OAuth users
    op.alter_column('users', 'hashed_password',
                    existing_type=sa.String(),
                    nullable=True)

    # Add OAuth fields
    op.add_column('users', sa.Column('google_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(20), nullable=False, server_default='email'))
    op.add_column('users', sa.Column('profile_picture', sa.Text(), nullable=True))

    # Create indexes
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)


def downgrade():
    # Remove indexes
    op.drop_index('ix_users_google_id', table_name='users')

    # Remove OAuth fields
    op.drop_column('users', 'profile_picture')
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'google_id')

    # Make hashed_password required again
    op.alter_column('users', 'hashed_password',
                    existing_type=sa.String(),
                    nullable=False)
