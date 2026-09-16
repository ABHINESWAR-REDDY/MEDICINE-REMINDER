"""create phase 4 caregiver assignments, medication doses, and audit logs tables

Revision ID: 007_create_phase4_tables
Revises: 006_add_single_admin_unique_index
Create Date: 2026-08-20 11:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_create_phase4_tables'
down_revision: Union[str, None] = '006_add_single_admin_unique_index'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Caregiver Patient Assignments Table
    op.create_table(
        'caregiver_patient_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('caregiver_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('assigned_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['caregiver_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('caregiver_id', 'patient_id', name='uq_caregiver_patient_assignment')
    )
    op.create_index('ix_caregiver_patient_assignments_id', 'caregiver_patient_assignments', ['id'], unique=False)
    op.create_index('ix_caregiver_patient_assignments_caregiver_id', 'caregiver_patient_assignments', ['caregiver_id'], unique=False)
    op.create_index('ix_caregiver_patient_assignments_patient_id', 'caregiver_patient_assignments', ['patient_id'], unique=False)

    # 2. Medication Doses Table
    op.create_table(
        'medication_doses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=False),
        sa.Column('medicine_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='SCHEDULED'),
        sa.Column('recorded_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['schedule_id'], ['medication_schedules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['medicine_id'], ['medicines.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('schedule_id', 'scheduled_time', name='uq_schedule_scheduled_time')
    )
    op.create_index('ix_medication_doses_id', 'medication_doses', ['id'], unique=False)
    op.create_index('ix_medication_doses_schedule_id', 'medication_doses', ['schedule_id'], unique=False)
    op.create_index('ix_medication_doses_medicine_id', 'medication_doses', ['medicine_id'], unique=False)
    op.create_index('ix_medication_doses_patient_id', 'medication_doses', ['patient_id'], unique=False)
    op.create_index('ix_medication_doses_scheduled_time', 'medication_doses', ['scheduled_time'], unique=False)
    op.create_index('ix_medication_doses_status', 'medication_doses', ['status'], unique=False)
    op.create_index('ix_doses_patient_scheduled_status', 'medication_doses', ['patient_id', 'scheduled_time', 'status'], unique=False)

    # 3. Audit Logs Table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=100), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)
    op.create_index('ix_audit_logs_actor_user_id', 'audit_logs', ['actor_user_id'], unique=False)
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_target_type', 'audit_logs', ['target_type'], unique=False)
    op.create_index('ix_audit_logs_target_id', 'audit_logs', ['target_id'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('medication_doses')
    op.drop_table('caregiver_patient_assignments')
