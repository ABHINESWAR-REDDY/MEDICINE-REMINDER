"""create medicine_references table

Revision ID: 005_create_medicine_reference_table
Revises: 004_create_medication_management_tables
Create Date: 2026-08-18 14:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_create_medicine_reference_table'
down_revision: Union[str, None] = '004_create_medication_management_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'medicine_references',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('dosage_form', sa.String(length=100), nullable=True),
        sa.Column('strength', sa.String(length=100), nullable=True),
        sa.Column('manufacturer', sa.String(length=255), nullable=True),
        sa.Column('indication', sa.String(length=255), nullable=True),
        sa.Column('classification', sa.String(length=100), nullable=True),
        sa.Column('frequency', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_medicine_references_id'), 'medicine_references', ['id'], unique=False)
    op.create_index(op.f('ix_medicine_references_name'), 'medicine_references', ['name'], unique=False)
    op.create_index(op.f('ix_medicine_references_normalized_name'), 'medicine_references', ['normalized_name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_medicine_references_normalized_name'), table_name='medicine_references')
    op.drop_index(op.f('ix_medicine_references_name'), table_name='medicine_references')
    op.drop_index(op.f('ix_medicine_references_id'), table_name='medicine_references')
    op.drop_table('medicine_references')
