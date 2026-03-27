"""add_institutional_trade_fields_manual

Revision ID: 08df85ab00a2
Revises: e1e3daed55a5
Create Date: 2026-03-27 05:12:52.410797

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '08df85ab00a2'
down_revision = 'e1e3daed55a5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add missing columns to trades
    op.add_column('trades', sa.Column('broker_raw_pnl', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('trades', sa.Column('broker_commission', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('trades', sa.Column('broker_swap', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('trades', sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('trades', sa.Column('reconciliation_status', sa.String(length=20), server_default='PENDING', nullable=True))
    
    # 2. Update Trade constraints (Drop old, add new)
    op.execute("ALTER TABLE trades DROP CONSTRAINT IF EXISTS check_risk_cap")
    op.execute("ALTER TABLE trades DROP CONSTRAINT IF EXISTS check_min_rr_ratio")
    op.create_check_constraint('check_min_rr_ratio', 'trades', 'rr_ratio >= 1.5 OR rr_ratio IS NULL')

    # 3. Ensure PostMortem has all fields (Handled in previous migration but double check)
    try:
        op.add_column('post_mortems', sa.Column('classification', sa.String(length=50), nullable=True))
    except:
        pass
    try:
        op.add_column('post_mortems', sa.Column('slippage_pips', sa.Float(), nullable=True))
    except:
        pass
    try:
        op.add_column('post_mortems', sa.Column('execution_latency_ms', sa.Float(), nullable=True))
    except:
        pass
    try:
        op.add_column('post_mortems', sa.Column('profit_efficiency', sa.Float(), nullable=True))
    except:
        pass

def downgrade() -> None:
    op.drop_column('trades', 'reconciliation_status')
    op.drop_column('trades', 'reconciled_at')
    op.drop_column('trades', 'broker_swap')
    op.drop_column('trades', 'broker_commission')
    op.drop_column('trades', 'broker_raw_pnl')
