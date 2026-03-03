"""add_opportunity_logs_table

Revision ID: 32966e01de9c
Revises: ac4ccbc94864
Create Date: 2026-03-02 13:59:53.573887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '32966e01de9c'
down_revision: Union[str, Sequence[str], None] = 'ac4ccbc94864'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create opportunity_logs table."""
    op.create_table(
        'opportunity_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True, index=True),
        sa.Column('symbol', sa.String(), nullable=False, index=True),
        sa.Column('timeframe', sa.String(), nullable=True),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('strategy_name', sa.String(), nullable=True),
        sa.Column('filter_name', sa.String(), nullable=False),
        sa.Column('filter_value', sa.Float(), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Drop opportunity_logs table."""
    op.drop_table('opportunity_logs')
