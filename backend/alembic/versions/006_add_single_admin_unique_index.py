"""add single admin partial unique index
 
Revision ID: 006_add_single_admin_unique_index
Revises: 005_create_medicine_reference_table
Create Date: 2026-08-19 18:28:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_single_admin_unique_index'
down_revision: Union[str, None] = '005_create_medicine_reference_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'uq_single_admin_role',
        'users',
        ['role'],
        unique=True,
        postgresql_where=sa.text("role = 'ADMIN'"),
        sqlite_where=sa.text("role = 'ADMIN'")
    )


def downgrade() -> None:
    op.drop_index(
        'uq_single_admin_role',
        table_name='users',
        postgresql_where=sa.text("role = 'ADMIN'"),
        sqlite_where=sa.text("role = 'ADMIN'")
    )
