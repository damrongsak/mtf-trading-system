"""add_regime_monitor_table

Revision ID: 7b55475a3ab9
Revises: c6fc08dced5a
Create Date: 2026-05-05 01:56:45.269300

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b55475a3ab9'
down_revision = 'c6fc08dced5a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'regime_monitor',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('gex_proxy', sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column('underlying_price', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('regime_type', sa.String(length=50), nullable=False),
        sa.Column('fragility_index', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('is_valid', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_noise', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_regime_monitor_symbol_timestamp', 'regime_monitor', ['symbol', 'timestamp'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_regime_monitor_symbol_timestamp', table_name='regime_monitor')
    op.drop_table('regime_monitor')
