"""add chat message deletion and conversation clear support

Revision ID: 009_add_chat_message_deletion
Revises: 008_create_chat_messages_table
Create Date: 2026-08-23 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009_add_chat_message_deletion'
down_revision: Union[str, None] = '008_create_chat_messages_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_messages', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('chat_messages', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('chat_messages', sa.Column('deleted_by', sa.Integer(), nullable=True))
    op.add_column('chat_messages', sa.Column('cleared_by_sender', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('chat_messages', sa.Column('cleared_by_recipient', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.create_index('ix_chat_messages_is_deleted', 'chat_messages', ['is_deleted'], unique=False)
    op.create_index('ix_chat_messages_deleted_by', 'chat_messages', ['deleted_by'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_chat_messages_deleted_by', table_name='chat_messages')
    op.drop_index('ix_chat_messages_is_deleted', table_name='chat_messages')
    op.drop_column('chat_messages', 'cleared_by_recipient')
    op.drop_column('chat_messages', 'cleared_by_sender')
    op.drop_column('chat_messages', 'deleted_by')
    op.drop_column('chat_messages', 'deleted_at')
    op.drop_column('chat_messages', 'is_deleted')
