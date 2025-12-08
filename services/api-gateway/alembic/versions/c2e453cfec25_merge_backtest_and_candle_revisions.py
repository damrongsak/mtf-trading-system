"""Merge backtest and candle revisions

Revision ID: c2e453cfec25
Revises: add_backtest_tables, e1533908c87a
Create Date: 2025-12-08 18:50:04.589982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2e453cfec25'
down_revision: Union[str, Sequence[str], None] = ('add_backtest_tables', 'e1533908c87a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
