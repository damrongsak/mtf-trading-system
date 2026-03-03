"""Add telegram_chat_mappings table

Revision ID: a8f3c9e2d1b4
Revises: f97fb85ac765
Create Date: 2026-02-09 13:22:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a8f3c9e2d1b4'
down_revision = 'f97fb85ac765'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'telegram_chat_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('linked_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('TRUE'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id')
    )
    op.create_index('idx_telegram_chat_id', 'telegram_chat_mappings', ['chat_id'])
    op.create_index('idx_telegram_user_id', 'telegram_chat_mappings', ['user_id'])


def downgrade():
    op.drop_index('idx_telegram_user_id', table_name='telegram_chat_mappings')
    op.drop_index('idx_telegram_chat_id', table_name='telegram_chat_mappings')
    op.drop_table('telegram_chat_mappings')
