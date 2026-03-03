"""Add AI Episodic Memory fields to journal_entries

Revision ID: 82acfe2850d1
Revises: fe4b9c1d2e3f
Create Date: 2026-03-03 19:39:38.474355

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '82acfe2850d1'
down_revision = 'fe4b9c1d2e3f'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add ONLY the missing fields to journal_entries 
    # (trade_id was already present and indexed in the DB schema previously!)
    op.add_column('journal_entries', sa.Column('is_ai_generated', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('journal_entries', sa.Column('ai_insight', sa.Text(), nullable=True))

def downgrade() -> None:
    # Drop columns
    op.drop_column('journal_entries', 'ai_insight')
    op.drop_column('journal_entries', 'is_ai_generated')
