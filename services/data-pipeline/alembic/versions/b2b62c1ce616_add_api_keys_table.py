"""add_api_keys_table

Revision ID: b2b62c1ce616
Revises: consolidated_head_v1
Create Date: 2026-03-04 09:16:57.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2b62c1ce616'
down_revision = 'consolidated_head_v1'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('api_key', sa.String(length=100), nullable=False),
        sa.Column('api_secret', sa.String(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('api_keys_user_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('api_keys_pkey')),
        sa.UniqueConstraint('api_key', name=op.f('api_keys_api_key_key'))
    )

def downgrade():
    op.drop_table('api_keys')
