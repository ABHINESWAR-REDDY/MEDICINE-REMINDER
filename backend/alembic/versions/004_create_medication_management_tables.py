"""create medication management tables (conditions, prescriptions, medicines, medication_schedules)

Revision ID: 004_create_medication_management_tables
Revises: 003_create_email_verification_codes_table
Create Date: 2026-08-17 23:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_create_medication_management_tables'
down_revision: Union[str, None] = '003_create_email_verification_codes_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Conditions table
    op.create_table(
        'conditions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conditions_id'), 'conditions', ['id'], unique=False)
    op.create_index(op.f('ix_conditions_user_id'), 'conditions', ['user_id'], unique=False)

    # 2. Prescriptions table
    op.create_table(
        'prescriptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('prescription_number', sa.String(length=100), nullable=True),
        sa.Column('doctor_name', sa.String(length=255), nullable=True),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prescriptions_id'), 'prescriptions', ['id'], unique=False)
    op.create_index(op.f('ix_prescriptions_user_id'), 'prescriptions', ['user_id'], unique=False)

    # 3. Medicines table
    op.create_table(
        'medicines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('prescription_id', sa.Integer(), nullable=True),
        sa.Column('condition_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('dosage_amount', sa.Float(), nullable=False),
        sa.Column('dosage_unit', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('medicine_form', sa.String(length=50), nullable=False, server_default='TABLET'),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['condition_id'], ['conditions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_medicines_id'), 'medicines', ['id'], unique=False)
    op.create_index(op.f('ix_medicines_user_id'), 'medicines', ['user_id'], unique=False)
    op.create_index(op.f('ix_medicines_prescription_id'), 'medicines', ['prescription_id'], unique=False)
    op.create_index(op.f('ix_medicines_condition_id'), 'medicines', ['condition_id'], unique=False)

    # 4. Medication Schedules table
    op.create_table(
        'medication_schedules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('medicine_id', sa.Integer(), nullable=False),
        sa.Column('frequency_type', sa.String(length=50), nullable=False),
        sa.Column('times_per_day', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('scheduled_times', sa.JSON(), nullable=False),
        sa.Column('dose_quantity', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['medicine_id'], ['medicines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_medication_schedules_id'), 'medication_schedules', ['id'], unique=False)
    op.create_index(op.f('ix_medication_schedules_medicine_id'), 'medication_schedules', ['medicine_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_medication_schedules_medicine_id'), table_name='medication_schedules')
    op.drop_index(op.f('ix_medication_schedules_id'), table_name='medication_schedules')
    op.drop_table('medication_schedules')

    op.drop_index(op.f('ix_medicines_condition_id'), table_name='medicines')
    op.drop_index(op.f('ix_medicines_prescription_id'), table_name='medicines')
    op.drop_index(op.f('ix_medicines_user_id'), table_name='medicines')
    op.drop_index(op.f('ix_medicines_id'), table_name='medicines')
    op.drop_table('medicines')

    op.drop_index(op.f('ix_prescriptions_user_id'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_id'), table_name='prescriptions')
    op.drop_table('prescriptions')

    op.drop_index(op.f('ix_conditions_user_id'), table_name='conditions')
    op.drop_index(op.f('ix_conditions_id'), table_name='conditions')
    op.drop_table('conditions')
