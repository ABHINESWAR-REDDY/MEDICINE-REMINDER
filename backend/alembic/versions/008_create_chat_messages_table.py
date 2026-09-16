"""create chat messages table

Revision ID: 008_create_chat_messages_table
Revises: 007_create_phase4_tables
Create Date: 2026-08-21 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_create_chat_messages_table'
down_revision: Union[str, None] = '007_create_phase4_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'], unique=False)
    op.create_index('ix_chat_messages_sender_id', 'chat_messages', ['sender_id'], unique=False)
    op.create_index('ix_chat_messages_recipient_id', 'chat_messages', ['recipient_id'], unique=False)
    op.create_index('ix_chat_sender_recipient', 'chat_messages', ['sender_id', 'recipient_id'], unique=False)
    op.create_index('ix_chat_recipient_read', 'chat_messages', ['recipient_id', 'is_read'], unique=False)


def downgrade() -> None:
    op.drop_table('chat_messages')
