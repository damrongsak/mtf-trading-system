"""Add hardening columns

Revision ID: b5727db261b4
Revises: merge_heads_v2
Create Date: 2026-03-06 10:50:53.009624

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5727db261b4'
down_revision = 'merge_heads_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add oanda_janitor_enabled to user_preferences
    op.add_column('user_preferences', sa.Column('oanda_janitor_enabled', sa.Boolean(), nullable=False, server_default='false'))
    
    # 2. Add broker_trade_id to trades
    # Check if column exists first (safer for shared DB)
    conn = op.get_bind()
    columns = sa.inspect(conn).get_columns('trades')
    column_names = [c['name'] for c in columns]
    
    if 'broker_trade_id' not in column_names:
        op.add_column('trades', sa.Column('broker_trade_id', sa.String(length=100), nullable=True))
    else:
        # If it exists, maybe lengthen it to 100 if it was 50
        op.alter_column('trades', 'broker_trade_id', type_=sa.String(length=100))

def downgrade() -> None:
    op.drop_column('user_preferences', 'oanda_janitor_enabled')
    op.drop_column('trades', 'broker_trade_id')
