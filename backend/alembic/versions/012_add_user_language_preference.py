"""add language preference to users table

Revision ID: 012_add_user_language_preference
Revises: 011_create_system_settings_table
Create Date: 2026-09-02 20:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012_add_user_language_preference'
down_revision: Union[str, None] = '011_create_system_settings_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [col['name'] for col in insp.get_columns('users')]
    if 'language' not in columns:
        op.add_column(
            'users',
            sa.Column('language', sa.String(length=10), nullable=False, server_default='en')
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [col['name'] for col in insp.get_columns('users')]
    if 'language' in columns:
        op.drop_column('users', 'language')
