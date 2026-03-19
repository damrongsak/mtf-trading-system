"""add is_active to funds table

Revision ID: 26a80d551e73
Revises: f98d1ccf91c9
Create Date: 2026-03-19 06:56:53.382965

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26a80d551e73'
down_revision = 'f98d1ccf91c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add as nullable
    op.add_column('funds', sa.Column('is_active', sa.Boolean(), nullable=True))
    
    # 2. Update existing rows
    op.execute("UPDATE funds SET is_active = true")
    
    # 3. Alter to NOT NULL and add server default
    op.alter_column('funds', 'is_active', nullable=False, server_default=sa.text('true'))


def downgrade() -> None:
    op.drop_column('funds', 'is_active')
