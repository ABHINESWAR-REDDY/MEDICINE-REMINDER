"""create system_settings table
 
Revision ID: 011_create_system_settings_table
Revises: 010_add_related_medicine_id_to_notifications
Create Date: 2026-08-24 12:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timezone
import json
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '011_create_system_settings_table'
down_revision: Union[str, None] = '010_add_related_medicine_id_to_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()
    if 'system_settings' not in tables:
        op.create_table(
            'system_settings',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('key', sa.String(length=100), nullable=False),
            sa.Column('value', sa.JSON(), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('category', sa.String(length=50), nullable=False, server_default='GENERAL'),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_by', sa.String(length=100), nullable=True),
        )
        op.create_index('ix_system_settings_id', 'system_settings', ['id'], unique=False)
        op.create_index('ix_system_settings_key', 'system_settings', ['key'], unique=True)
        op.create_index('ix_system_settings_category', 'system_settings', ['category'], unique=False)

        # Seed default notification settings row
        default_notification_settings = {
            "patient_medication_reminders_enabled": True,
            "patient_missed_dose_alerts_enabled": True,
            "patient_refill_alerts_enabled": True,
            "patient_polling_interval_seconds": 30,
            "caregiver_missed_dose_alerts_enabled": True,
            "caregiver_refill_alerts_enabled": True,
            "caregiver_adherence_risk_alerts_enabled": True,
            "caregiver_patient_chat_alerts_enabled": True,
            "system_security_alerts_enabled": True,
            "system_operational_alerts_enabled": True,
        }

        settings_table = sa.table(
            'system_settings',
            sa.column('key', sa.String),
            sa.column('value', sa.JSON),
            sa.column('description', sa.String),
            sa.column('category', sa.String),
            sa.column('updated_at', sa.DateTime(timezone=True)),
            sa.column('updated_by', sa.String),
        )

        op.bulk_insert(settings_table, [
            {
                'key': 'notification_settings',
                'value': default_notification_settings,
                'description': 'Platform-wide notification dispatch and alert rules',
                'category': 'NOTIFICATIONS',
                'updated_at': datetime.now(timezone.utc),
                'updated_by': 'SYSTEM_INIT',
            }
        ])


def downgrade() -> None:
    op.drop_index('ix_system_settings_category', table_name='system_settings')
    op.drop_index('ix_system_settings_key', table_name='system_settings')
    op.drop_index('ix_system_settings_id', table_name='system_settings')
    op.drop_table('system_settings')
