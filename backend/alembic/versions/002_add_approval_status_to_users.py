"""add approval_status to users table

Revision ID: 002_add_approval_status_to_users
Revises: 001_create_users_table
Create Date: 2026-08-17 20:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_approval_status_to_users'
down_revision: Union[str, None] = '001_create_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('approval_status', sa.String(length=50), nullable=False, server_default='APPROVED')
    )


def downgrade() -> None:
    op.drop_column('users', 'approval_status')
