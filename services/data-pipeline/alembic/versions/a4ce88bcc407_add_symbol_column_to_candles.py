"""Add symbol column to candles

Revision ID: a4ce88bcc407
Revises: 60391347e571
Create Date: 2026-02-08 10:50:58.014429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a4ce88bcc407"
down_revision: Union[str, Sequence[str], None] = "60391347e571"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add symbol to candles with backfill."""
    # 1. Column already exists as nullable from initial schema
    
    # 2. Backfill from market_symbols table
    op.execute("""
        UPDATE candles c
        SET symbol = ms.symbol
        FROM market_symbols ms
        WHERE c.market_symbol_id = ms.id
    """)
    
    # 3. Make column NOT NULL after backfill
    op.alter_column("candles", "symbol", nullable=False)
    
    # 4. Create indexes
    op.create_index(op.f("ix_candles_symbol"), "candles", ["symbol"], unique=False)
    op.create_index("ix_candles_symbol_timeframe_timestamp", "candles", ["symbol", "timeframe", "timestamp"], unique=False)


def downgrade() -> None:
    """Downgrade schema: Remove symbol column and indexes."""
    op.drop_index("ix_candles_symbol_timeframe_timestamp", table_name="candles")
    op.drop_index(op.f("ix_candles_symbol"), table_name="candles")
    # Column persists due to initial schema
