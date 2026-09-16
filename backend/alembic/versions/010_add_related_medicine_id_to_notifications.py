"""add related_medicine_id to notifications table

Revision ID: 010_add_related_medicine_id_to_notifications
Revises: 009_add_chat_message_deletion
Create Date: 2026-08-23 21:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_add_related_medicine_id_to_notifications'
down_revision: Union[str, None] = '009_add_chat_message_deletion'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely add column if not existing
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('notifications')]
    if 'related_medicine_id' not in cols:
        op.add_column('notifications', sa.Column('related_medicine_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_notifications_related_medicine_id', 'notifications', 'medicines', ['related_medicine_id'], ['id'], ondelete='CASCADE')
        op.create_index('ix_notifications_related_medicine_id', 'notifications', ['related_medicine_id'], unique=False)
        op.create_index('ix_notifications_user_type_medicine', 'notifications', ['user_id', 'type', 'related_medicine_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_notifications_user_type_medicine', table_name='notifications')
    op.drop_index('ix_notifications_related_medicine_id', table_name='notifications')
    op.drop_constraint('fk_notifications_related_medicine_id', 'notifications', type_='foreignkey')
    op.drop_column('notifications', 'related_medicine_id')
